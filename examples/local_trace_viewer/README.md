# Local synthetic trace viewer

This English-language client example generates 1/5/25-record synthetic graphs through the installed stdio MCP server, validates each graph and writes one standalone HTML file. Open it directly in a local browser. It uses no HTTP server, external assets, AI provider or real-document input. It does not change server APIs, package versions or RawEvidence policy.

The viewer supports scenario selection, insight/finding/item/evidence/source drill-down, breadcrumbs, back/root navigation, search, counts and safe metadata. It is a SAVED synthetic snapshot, not a live server connection, reasoning engine or proof that claims are true. Client attachment binding remains unverified.

## Generate

Install the reviewed Core 0.2.0 and MCP 0.1.0a4 wheels plus their pinned runtime closure into an isolated environment. From outside source, invoke the example using that environment's Python:

```sh
<installed-python> -I <source>/examples/local_trace_viewer/generate.py --output <new-output>/index.html
```

Use Docker with `--network none` for the recorded offline workflow; mount the example read-only and a separate output directory writable. The generator refuses to overwrite an existing output. Keep the pinned pair and its original artifacts unchanged.

## Privacy and limits

Only fixed synthetic normalized statements and allowlisted metadata are exported. Raw payloads are generated in memory and never written. Evidence must be synthetic, redacted and contract version 2; raw-content fields are rejected. Client responses and captured server stderr are checked in memory before export. The page has a no-network Content Security Policy and renders data via textContent; embedded JSON escapes HTML delimiters.

The generator accepts no external data source or arbitrary user graph. Do not repurpose this example to export real evidence, diagnostics or private source content. Static snapshots do not update after a server Reset; their limitation is visible in the page. This example is for technical evaluation only.

## Optional browser acceptance check

On Windows, the dependency-free browser check was exercised with Node 26.9.0 and the installed Microsoft Edge. It creates a separate temporary browser profile, checks drill-down/back/root navigation, exact grouped references, scenario changes, search/empty state, mobile overflow and zero external page requests, then closes its own browser and removes that profile. It does not use the user's browser session.

```text
node browser_check.mjs <generated-html> <new-evidence-directory> <edge-executable>
```

The evidence directory receives browser-results.json and desktop/mobile screenshots. These generated artifacts stay outside the repository; do not commit them or use the checker against a page containing real evidence. Normal viewing needs only a local browser, not Node.

## Conflicting upload reports

Add `--conflicting-uploads` to start with a guided walkthrough. Compare the
three reports and choose whether to lower the size limit or investigate first.
Select **Explore the evidence trail** to open the graph and follow its references.
The graph validates the links; it does not establish a size limit or prove the
cause of the failure.

Generating the viewer requires the Alpha 4 package pair and Python 3.10 or
newer with compatible dependencies. After generation, open the HTML in a
browser; viewing it does not require Python.
