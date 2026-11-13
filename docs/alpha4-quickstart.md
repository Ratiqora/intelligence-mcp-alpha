# Alpha 4 quickstart

Download the Alpha 4 files from the [release page](https://github.com/Ratiqora/intelligence-mcp-alpha/releases/tag/v0.1.0-alpha.4). Start from a directory containing those files.

## 1. Get the matching files

Keep these four files in the same directory:

- `ratiqora_intelligence_mcp-0.1.0a4-py3-none-any.whl`
- `ratiqora_intelligence_core-0.2.0-py3-none-any.whl`
- `alpha-runtime-constraints.txt`
- `SHA256SUMS.txt` from the same trusted handoff or release

Use Python 3.10 or 3.13. The packaged trial does not need a Git clone, a GitHub token, an API key,
or a separately configured MCP client. Pip needs access to the pinned dependencies on a package
index, or a compatible local wheelhouse for offline installation.

## 2. Verify the downloads

Compare the three file hashes with their entries in `SHA256SUMS.txt`. Stop if an entry is absent
or differs.

**Linux:**

```sh
sha256sum ratiqora_intelligence_mcp-0.1.0a4-py3-none-any.whl ratiqora_intelligence_core-0.2.0-py3-none-any.whl alpha-runtime-constraints.txt
```

**Windows PowerShell:**

```powershell
Get-FileHash -Algorithm SHA256 ratiqora_intelligence_mcp-0.1.0a4-py3-none-any.whl,ratiqora_intelligence_core-0.2.0-py3-none-any.whl,alpha-runtime-constraints.txt
```

## 3. Install and run the synthetic trial

Run these commands from the download directory, outside any source checkout. Stop if a command fails.
Use the matching Core and MCP wheels together.

**Linux:**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -c alpha-runtime-constraints.txt ./ratiqora_intelligence_core-0.2.0-py3-none-any.whl ./ratiqora_intelligence_mcp-0.1.0a4-py3-none-any.whl
.venv/bin/python -m pip check
.venv/bin/ratiqora-alpha-trial
```

For a Linux offline run, with a complete compatible wheelhouse, set
`PIP_NO_INDEX=1` and `PIP_FIND_LINKS=/absolute/path/to/wheelhouse` for the install command.

**Windows PowerShell:**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c alpha-runtime-constraints.txt .\ratiqora_intelligence_core-0.2.0-py3-none-any.whl .\ratiqora_intelligence_mcp-0.1.0a4-py3-none-any.whl
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ratiqora-alpha-trial.exe
```

Use `py -3.10` instead if testing Python 3.10. Success means the trial exits with code zero and
prints JSON with `"valid": true` and one of each: source, evidence, item, finding, and insight.

Use only synthetic inputs for this quickstart. The trial runs locally over stdio and is not
production certification. To clean up, close the trial and remove the dedicated `.venv`.
For scope, reporting, and rollback see the [Alpha boundary](alpha-release-boundary.md),
[security policy](../SECURITY.md).
