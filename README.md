# Ratiqora Intelligence MCP — Alpha 4

Ratiqora helps MCP developers trace a conclusion back to the observations that support it. The local server checks evidence integrity and graph references, and exposes redacted evidence metadata over stdio.

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

## Try it

1. Download the two wheels, constraints and checksum file from [Alpha 4](https://github.com/Ratiqora/intelligence-mcp-alpha/releases/tag/v0.1.0-alpha.4).
2. Follow the [quickstart](docs/alpha4-quickstart.md) for Windows or Linux.
3. Run the synthetic trial. To explore the graph visually, generate the [local trace viewer](examples/local_trace_viewer/README.md) and open the resulting HTML in a browser. No model API key is needed.

Alpha 4 is an experimental single-project, in-memory runtime. Use synthetic data for these examples. It is not a hosted service, a general file connector or a production system.

## Contribute

A useful first contribution is a synthetic trace with conflicting customer observations. Start with the [example generator](examples/local_trace_viewer/generate.py): keep both observations traceable, avoid presenting an unproven cause as fact, and verify the generated viewer opens without network access. Open an issue with the proposed scenario or submit a focused PR with reproduction steps. Never include real customer data or raw evidence.

This repository is a curated snapshot of the MCP source. The matching Core wheel includes its Python implementation. See [LICENSE](LICENSE), [NOTICE](NOTICE) and [SECURITY.md](SECURITY.md).
