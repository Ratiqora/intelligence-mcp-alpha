# Ratiqora — Evidence Traceability for MCP

**Trace a decision back to the observations and sources behind it.** Ratiqora Alpha 4 is an open-source, local Model Context Protocol (MCP) server for evidence traceability and provenance. It checks evidence integrity and graph references and exposes redacted evidence metadata over stdio.

| Start here | What you can do |
| --- | --- |
| **[Read a sample decision brief](examples/decision_workbench/samples/checkout-decision-brief.md)** | See how one successful checkout challenges a proposed Safari-wide workaround. Read it right here on GitHub. |
| **[Try the one-minute browser demo](https://ratiqora.github.io/intelligence-mcp-alpha/)** | Decide whether to change a photo upload limit, straight from your browser. Prefer to try it offline? [Download the same HTML file](https://github.com/Ratiqora/intelligence-mcp-alpha/releases/download/v0.1.0-alpha.4/ratiqora-alpha4-demo.html). |
| **[Run the local MCP server](docs/alpha4-quickstart.md)** | Install the Alpha packages and run the synthetic trial on Windows or Linux. |

In the checkout example, one Safari customer got stuck, another completed checkout, and a similar stall occurred in Chrome. Follow the counterexample to its source and see why changing the experience for every Safari user would outrun the evidence.

## A two-minute example: photo uploads

Three customers reported failed uploads for photos above 10 MB. Another uploaded a 2 MB photo successfully. These observations make file size worth testing, but they do not establish a 10 MB limit.

| Trace step | Synthetic example |
| --- | --- |
| Insight | Compare upload outcomes before changing the form. |
| Finding | The failed uploads were larger than the successful one; format and other causes remain untested. |
| Item | The reports associate larger files with failures in this small sample. |
| Evidence | The reports are linked by ID and checked against the SHA-256 of their exact bytes. The raw payload is not returned. |
| Source | A synthetic batch of customer feedback. |

This table is an illustrative scenario. The packaged trial builds its own synthetic graph. A valid graph has intact references; it does not prove the conclusion or authenticate a source.

The walkthrough’s three-report scenario can be turned into a [one-page decision brief](examples/local_trace_viewer/README.md#generate-a-decision-brief) with supporting and conflicting reports, open questions, and a next step.

## Build your own decision brief

Run the [local Decision Workbench](examples/decision_workbench/README.md) to link your observations to public or fictional source references. Try the [sample checkout CSV](examples/decision_workbench/samples/checkout-observations.csv) before entering your own observations. Ratiqora checks the internal links before you download an offline HTML or Markdown brief. You mark which observations support or challenge your hypothesis, then write your own conclusion.

## Which version am I running?

The [Alpha 4 downloads](https://github.com/Ratiqora/intelligence-mcp-alpha/releases/tag/v0.1.0-alpha.4)
are MCP `0.1.0a4`. This checkout builds `0.1.0a5.dev0`, which includes
caller-declared authorship and the newer MCP input limits. To try the development
wheel, use the [one-command checkout trial](docs/alpha4-quickstart.md#run-the-development-wheel-from-a-checkout).
The browser demo needs no installation.

## Try it

1. Download the two wheels, constraints and checksum file from [Alpha 4](https://github.com/Ratiqora/intelligence-mcp-alpha/releases/tag/v0.1.0-alpha.4).
2. Follow the [quickstart](docs/alpha4-quickstart.md) for Windows or Linux.
3. Run the synthetic trial. To explore the graph visually, generate the [local trace viewer](examples/local_trace_viewer/README.md) and open the resulting HTML in a browser. Add `--conflicting-uploads` to explore two equally large photos with opposite outcomes. The generated page needs only a browser. No model API key is needed.

Alpha 4 is an experimental single-project, in-memory runtime. Use synthetic data for these examples. It is not a hosted service, a general file connector or a production system.

## Contribute

- **Demo feedback:** [Tell us what was clear and where you got stuck](https://github.com/Ratiqora/intelligence-mcp-alpha/issues/new?title=Alpha+4+demo+feedback&body=What+did+you+think+the+demo+was+asking+you+to+do+when+it+first+opened%3F%0A%0AWhat+product+decision%2C+if+any%2C+did+it+help+you+make%3F%0A%0AWhere%2C+if+anywhere%2C+did+you+get+stuck%3F%0A%0APlease+leave+out+personal+information+and+real+customer+data.%0A). This opens a public GitHub issue draft.
- **Docs and packaging:** [Test the quickstart on a fresh Windows or Linux environment](https://github.com/Ratiqora/intelligence-mcp-alpha/issues/3) and report the first step that could be clearer.
- **Discuss the checkout story:** [Which observation changed what you would test next?](https://github.com/Ratiqora/intelligence-mcp-alpha/discussions/21) Read the fictional case and share your reasoning. No install required.

Write UI text, documentation, examples, and test fixtures in English. Use synthetic data and include reproduction steps with a focused PR. Never include real customer data or raw evidence.

This repository is a curated snapshot of the MCP source. The matching Core wheel includes its Python implementation. See [LICENSE](LICENSE), [NOTICE](NOTICE) and [SECURITY.md](SECURITY.md).
