"""Build committed MCP source and run its installed console trial outside the checkout."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = "ratiqora-intelligence-mcp"
CORE = (
    "https://github.com/Ratiqora/intelligence-mcp-alpha/releases/download/v0.1.0-alpha.4/"
    "ratiqora_intelligence_core-0.2.0-py3-none-any.whl"
    "#sha256=015805f60d811646eed291873f4fb8244664e1038c172f832529ae4e4d99525f"
)
COUNTS = dict.fromkeys(("sources", "evidence", "items", "findings", "insights"), 1)
ENV = {k: v for k, v in os.environ.items() if k.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
ENV.update(PYTHONNOUSERSITE="1", PIP_DISABLE_PIP_VERSION_CHECK="1")


def run(args, cwd, *, capture=False):
    result = subprocess.run(args, cwd=cwd, env=ENV, text=True, check=True,
                            stdout=subprocess.PIPE if capture else None, timeout=300)
    return result.stdout.strip() if capture else None


def check(work):
    commit = run(["git", "rev-parse", "HEAD"], ROOT, capture=True)
    archive = work / "source.zip"
    run(["git", "archive", "--format=zip", "-o", archive, commit], ROOT)
    source = work / "source"
    with ZipFile(archive) as files:
        files.extractall(source)
    pins = source / "requirements/alpha-runtime-constraints.txt"
    expected, = (line.split("==")[1] for line in pins.read_text().splitlines()
                 if line.startswith(DIST + "=="))
    print(f"Building {DIST} {expected} from {commit}", flush=True)
    wheels = work / "wheels"
    python = Path(sys.executable)
    # pip's build isolation installs the backend declared by the archived pyproject.
    run([python, "-m", "venv", work / "build-env"], work)
    bindir = Path("Scripts") if os.name == "nt" else Path("bin")
    interpreter = "python.exe" if os.name == "nt" else "python"
    builder = work / "build-env" / bindir / interpreter
    run([builder, "-Im", "pip", "wheel", "--no-deps", "-w", wheels, source], work)
    wheel, = wheels.glob("*.whl")
    run([python, "-m", "venv", work / "runtime"], work)
    binpath = work / "runtime" / bindir
    runtime = binpath / interpreter
    run([runtime, "-Im", "pip", "install", "-c", pins, CORE, wheel], work)
    run([runtime, "-Im", "pip", "check"], work)
    # Both imports must resolve inside this new environment, not the archived source.
    probe = """
import importlib.metadata as md, json, sysconfig
from pathlib import Path
import intelligence_core, intelligence_mcp
site = Path(sysconfig.get_path("purelib")).resolve()
if not all(Path(m.__file__).resolve().is_relative_to(site) for m in (intelligence_mcp, intelligence_core)):
    raise SystemExit("Imports must come from the fresh environment")
print(json.dumps([md.version("ratiqora-intelligence-mcp"), intelligence_mcp.__version__]))
"""
    if json.loads(run([runtime, "-Ic", probe], work, capture=True)) != [expected, expected]:
        raise ValueError("Installed metadata and module must match the checkout version pin")
    trial = binpath / ("ratiqora-alpha-trial.exe" if os.name == "nt" else "ratiqora-alpha-trial")
    report = json.loads(run([trial], work, capture=True))
    counts = report.get("counts")
    if (report.get("version") != expected or report.get("valid") is not True or counts != COUNTS
            or any(type(n) is not int for n in counts.values())):
        raise ValueError("Installed trial returned an unexpected version, validation or counts")
    print(json.dumps({"commit": commit, "version": expected, "valid": True, "counts": counts,
                      "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}, sort_keys=True))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="ratiqora-wheel-") as directory:
        check(Path(directory))
