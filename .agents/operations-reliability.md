# Operations And Reliability

Precedence for this repository: `.agents/AGENTS.md` and
`.agents/workflows/extraction.md` define the current Siemens operating model:
local PDFs, deterministic generated outputs, bundled-runtime tests, and explicit
regeneration. Use this file as subordinate reliability guidance.

Use this guidance for deployment-facing code, migrations, release artifacts,
service configuration, health checks, runbooks, and changes that cross external
system boundaries.

## Deployment Boundaries

- Identify the deployment target and scope before changing deployment code or
  docs.
- Separate build, release, deploy, activation, migration, and rollback
  responsibilities.
- CI may validate, build, test, and publish artifacts, but production deployment
  authority should remain with the approved deployment system.
- Runtime artifacts should not depend on repository-relative files on production
  hosts unless that is the explicit deployment contract.
- Generated config, service definitions, package data, and installed scripts are
  public contracts once operators depend on them.

## Migrations And Schema Safety

- Prefer explicit migration entrypoints for release DDL.
- Long-running services should validate required schema before serving traffic
  or processing durable work.
- Distinguish migration-time permissions from steady-state runtime permissions.
- Treat schema validation failures and permission failures as deployment
  blockers, not errors to paper over with ad hoc manual changes.
- Keep migration order, dry-run behavior, and idempotency requirements
  documented and tested.

## Health, Readiness, And Status

- Health checks should answer whether the process is alive.
- Readiness checks should answer whether the service can safely perform its
  responsibilities.
- Status output should be bounded, non-secret, and useful to operators.
- Metrics should expose actionable behavior without high-cardinality or
  sensitive labels.
- Admin endpoints should default to the narrowest safe exposure and require an
  intentional access-control decision before wider exposure.

## External Systems

- Isolate databases, queues, object stores, identity providers, email providers,
  payment systems, and third-party APIs behind small clients or repositories.
- Set explicit timeouts and retry policies.
- Make recovery behavior clear: retry, dead-letter, quarantine, compensation,
  operator action, or fail-fast.
- Preserve idempotency across retries, duplicate messages, process restarts, and
  repeated deployment commands.
- Do not let optional downstream outages corrupt durable local state.

## Rollback And Compatibility

- Define rollback before deployment when migrations, data formats, or release
  artifacts change.
- If the previous runtime cannot read the new schema or data format, document
  the restore or forward-fix requirement.
- Keep old and new versions compatible during rolling deploys when the
  deployment model requires overlap.
- Treat release asset replacement or republishing as an integrity event that
  requires review.

## Runbooks

Runbooks should include:

- Symptoms and likely causes.
- Safe diagnostic commands.
- Health/readiness/status checks.
- Recovery steps and rollback constraints.
- Escalation criteria.
- Secret-handling warnings when diagnostics can expose private data.

Keep runbooks practical and current with the actual deployment model.
