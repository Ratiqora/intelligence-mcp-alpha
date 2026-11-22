# Alpha release boundary

Status: **experimental; not production-ready**

## Support

The current Alpha is a local stdio runtime for bounded technical evaluation with synthetic data or
one explicitly selected public UTF-8 text file under the documented trusted-preload constraints.
Support is best effort through GitHub issues. Reports should include package version, MCP client,
failed operation, safe entity IDs, bounded diagnostic code/category, validation status, and the
safety flags from `get_support_report`.

Never attach RawEvidence, tool inputs, secrets, customer material, private documents, exception
messages, project identifiers, or local filesystem paths. Security reports follow
[SECURITY.md](../SECURITY.md), not public issues.

## Compatibility

- Python 3.10 and newer and local stdio transport define the supported runtime boundary.
- MCP-to-Core compatibility is enforced by the exact declared Core package version.
- Patch Alpha releases should not intentionally break documented tool names or safe response fields.
- While the version remains 0.x, a minor Alpha release may change tools or responses only with
  release notes, updated deterministic tests, compatibility evidence, and owner approval.
- Resources and tools outside the documented Alpha surface have no compatibility promise.
- Hosted transport, persistence, OAuth, multi-user behavior, connectors, providers, and product or
  domain features are unsupported and have no compatibility promise.

There is no production SLA, uptime guarantee, hosted service, data durability promise, or support
commitment for downstream private integrations.

## Release discipline

A release candidate must pass tests, lint, build, packaged-client smoke tests, fresh artifact
installation, and privacy/secret checks. Publication or visibility changes require separate founder
authorization.
## Limits and trace reads in the source checkout

The local MCP server accepts up to 64 KiB of UTF-8 model-supplied synthetic
evidence, 16 KiB per normalized observation or finding/insight statement,
256 IDs per reference list, and 256 entities total per project. A confirmed
reset clears the project. The separate trusted-host file limit remains 1 MiB.
These are application-level checks, not transport limits. The Alpha 4 release
wheels predate the new model-input and project limits.

A trace read returns the requested entity and its **direct** references.
For example, after registering insight i1 → finding f1 → item o1 → evidence
e1 → source s1, read `ratiqora://trace/i1`, follow its supporting finding ID,
then the finding’s item ID, the item’s evidence ID and the evidence’s
`source_record_id`. Each hop is a separate read. Evidence bytes are redacted;
authored summaries and statements are visible. A matching hash verifies the
submitted bytes, not the author's identity, public status or source authenticity.

In the development checkout the MCP text limits are measured in UTF-8 bytes:
project/entity IDs (including references and reset confirmation), display name,
source instance and collector method: 256 each; external reference: 4096;
timestamp input: 64; expected SHA-256 text: 71. Application size, list and
project-capacity errors use `RQ-LIMIT-001`. They do not echo the argument.
These checks operate on decoded arguments; they do not limit transport frames.

### Declare who produced a statement (source checkout)

For `register_item`, `register_finding` and `register_insight`, declare who or
what produced the **text**, independently of the method that registers it:

| producer_kind | Required details |
| --- | --- |
| `human` | `actor_ref`: a shareable pseudonymous author reference |
| `ai_assisted` | `provider` and `model`: supply the actual values |
| `deterministic` | Explicitly select only for rule-generated text, such as the trial fixture |

The producer fields are visible in tool and resource responses. Do not supply
secrets or private identifiers. Each detail is limited to 256 UTF-8 bytes.
Provider and model are valid only for AI assistance. The returned
`producer.attribution = "caller_declared"` is not identity verification;
`producer.method` identifies the registration operation.

**Client migration:** Earlier clients could omit attribution. The checkout
now rejects a missing or incomplete declaration without recording the entity.
Do not substitute placeholder identities. The published Alpha 4 wheels keep
their original interface; use tool discovery when supporting both versions.
