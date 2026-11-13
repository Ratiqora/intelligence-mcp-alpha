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