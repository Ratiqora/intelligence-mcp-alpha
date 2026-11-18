# Local Decision Workbench

Install the Alpha dependencies from the [quickstart](../../docs/alpha4-quickstart.md).
From the repository checkout, run these commands with that environment's Python:

```sh
python -I examples/decision_workbench/run.py
```

Open <http://127.0.0.1:8765/>. You can use `--port 8766` if the port is in use.

1. Enter the decision question and the hypothesis you want to test. For the [checkout CSV](samples/checkout-observations.csv), use “Every Safari checkout fails.”
2. Add public or fictional source references. Add observations and select a source and role for each. The successful Safari payment challenges that hypothesis; the Chrome stall adds context about the wallet flow.
3. Write your conclusion separately (for example, “Leave the Safari flow as it is for now”). Enter what remains unknown and the next step. Check references and download the validated brief.

Use **Jump to next step** at the top of the preview to go to the proposed action. The preview
groups observations marked **Challenges the hypothesis** first. Use **Go to source** to jump from
any observation to its listed reference. Choose **Download HTML for review**
to give someone the same linked brief. The file opens offline in a browser without the Workbench,
scripts, or external resources. **Download Markdown** remains available for text editing and uses
a space at each line break in a source reference, so words remain separate.

If you remove a source already referenced by an observation, the workbench asks you to fix the link
before it will produce a brief. Core validates the finding, observation, evidence and source links.
It does not open the cited material, judge the finding, or check whether the assigned roles are correct.
The evidence records bind author-entered observation summaries in memory. The report includes those
summaries and source references with no separate raw evidence payload or integrity digest.

Use public or fictional material. The workbench listens only on your machine. It creates no saved
drafts and does not fetch sources. Both download formats include your entries. Review them
before sharing, and use public or fictional material only.

## Import multiple observations

In **Link your observations**, open **Import observations from CSV** and click
**Replace rows from CSV** after selecting your file. Use UTF-8 with the columns
below, up to 12 observations and 64 KiB. Quote fields containing commas, quotes,
or newlines. The import reuses identical source references of the same type.

```csv
observation,source_reference,source_type,role
"Upload failed at 12 MB","Fictional report A, page 2",fictional,supports
"Upload worked at 12 MB","Fictional report B, page 1",fictional,challenges
```

Use `fictional` or `public` as the source type, and `supports`, `challenges`,
or `context` as the role relative to your hypothesis. A valid import replaces the source and observation
rows, leaving the decision text in place. A rejected import keeps the draft and any validated
preview. Imports run locally; the workbench does not fetch the cited sources.
