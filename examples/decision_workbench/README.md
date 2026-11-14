# Local Decision Workbench

Install the Alpha dependencies from the [quickstart](../../docs/alpha4-quickstart.md).
From the repository checkout, run these commands with that environment's Python:

```sh
python -I examples/decision_workbench/run.py
```

Open <http://127.0.0.1:8765/>. You can use `--port 8766` if the port is in use.

1. Enter a question and your finding.
2. Add public or fictional source references. Add observations and select a source and role for each.
3. Enter what remains unknown and the next step. Check references and download the validated brief.

If you remove a source already referenced by an observation, the workbench asks you to fix the link
before it will produce a brief. Core validates the finding, observation, evidence and source links.
It does not open the cited material, judge the finding, or check whether the assigned roles are correct.
The evidence records bind author-entered observation summaries in memory. The report includes those
summaries and source references with no separate raw evidence payload or integrity digest.

Use public or fictional material. The workbench listens only on your machine. It creates no saved
drafts and does not fetch sources. Your entries are included in the Markdown file you download.
