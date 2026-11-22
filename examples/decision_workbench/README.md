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

Use public or fictional material. The workbench listens only on your machine. It does not save drafts
automatically or fetch sources. All downloads include your entries; review them before sharing.

## Continue a brief another day

After checking references, choose **Save editable brief**. Keep the downloaded JSON file
on your device. In a fresh local Workbench, choose **Continue a saved brief**, select that
file, and click **Open editable brief**. The Workbench rechecks the references and asks
before replacing existing entries. Add the new observation, revise the next step, and
check references again before downloading the updated brief.

The file contains your decision text, observation summaries, roles and source references.
It does not contain cited documents. HTML and Markdown are for readers; use JSON to resume editing.

## Import multiple observations

In **Link your observations**, open **Import observations from CSV** and click
**Add new rows from CSV** after selecting your file. Use UTF-8 with the columns
below, up to 12 observations and 64 KiB. Quote fields containing commas, quotes,
or newlines. The import reuses identical source references of the same type.

```csv
observation,source_reference,source_type,role
"Upload failed at 12 MB","Fictional report A, page 2",fictional,supports
"Upload worked at 12 MB","Fictional report B, page 1",fictional,challenges
```

Use `fictional` or `public` as the source type, and `supports`, `challenges`,
or `context` as the role relative to your hypothesis. Adding rows keeps existing observations, source IDs and decision text. A matching observation
from the same source is skipped, even if the incoming role differs; edit its role in the form
if your interpretation has changed. **Replace rows from CSV** still replaces all source and
observation rows. If an import is rejected, the draft and any validated preview stay as they were. Imports run locally; the workbench does not fetch the cited sources.

**Try a second round:** After generating the first checkout brief, add the
[controlled replay CSV](samples/checkout-replay.csv) in the same open Workbench.
The replay becomes O4 with source S4. Keep the Safari conclusion, change the next
step to checking the wallet callback in staging, and generate a new brief. Adding the
same replay again will not count it as a second observation.

### Use the decision in a meeting

After checking references, choose the observation to share and mark the decision
as changed, unchanged, or a first decision. Review the three lines and choose
**Copy decision update** to paste them into a team document. The last observation
is selected initially; the Workbench does not infer what changed. A source
reference is a citation supplied by the author. Recheck after editing the draft.
