# Review Checklist

Precedence for this repository: review Siemens extractor changes against
`.agents/AGENTS.md`, `.agents/architecture.md`, `.agents/workflows/extraction.md`,
and `.agents/checklists/refactor_checklist.md` first. Use this checklist as a
subordinate review aid.

Use this checklist before handing off code changes or when reviewing another
change. Lead with correctness, compatibility, security, and operations risk.

## Scope And Compatibility

- The diff is limited to the requested behavior and affected docs.
- Public imports, package names, console scripts, CLI flags, config keys,
  environment variables, generated paths, and file formats remain compatible
  unless the change intentionally updates the contract.
- Default values, dry-run output, logs consumed by automation, metrics, and
  status responses remain stable or have a documented migration path.
- Generated artifacts and lockfiles changed only when required.
- Existing user changes and unrelated worktree state were preserved.

## Data And Persistence

- Schema changes are explicit, reviewed, and covered by migration tests.
- Migrations are idempotent where the deployment model requires repeatability.
- Runtime startup does not silently own release DDL unless that is the explicit
  project contract.
- Transactions commit or roll back as one unit where partial writes would create
  corruption or duplicate durable effects.
- Reprocessing, retries, duplicate payloads, duplicate messages, and repeated
  commands are idempotent or intentionally rejected.
- Data retention, cleanup, archive, and quarantine behavior remain documented
  and testable.

## External Systems

- Network, database, queue, storage, SMTP, payment, identity, and third-party
  calls have explicit timeout, retry, backoff, and recovery behavior.
- Failed external calls have clear retry, dead-letter, quarantine, or operator
  recovery behavior.
- External-system outages do not block unrelated local transactions unless the
  product contract requires synchronous failure.
- Integration behavior is isolated behind clients, repositories, adapters, or
  service objects.

## Observability And Operations

- Important new behavior is observable through structured logs, metrics, traces,
  health checks, readiness checks, status output, or admin endpoints as
  appropriate.
- Metrics avoid high-cardinality labels and secret-bearing values.
- Health and readiness checks represent real dependencies and startup state.
- Deployment artifacts, write paths, service ownership, migration order, and
  rollback expectations still match the documented runtime model.
- Operator-facing command examples are safe, bounded, and current.

## Security And Secrets

- Credentials are loaded through approved config or secret-management paths.
- Secrets are not logged, embedded in examples, committed in fixtures, captured
  in screenshots, or written into generated plaintext artifacts.
- Test data, sample payloads, and docs examples are synthetic or sanitized.
- Access control, authentication, authorization, and admin endpoints remain
  compatible with the threat model.
- Dependency changes are justified and covered by an audit when tooling exists.

## Tests And Docs

- Focused tests cover the changed behavior.
- Regression tests cover fixed bugs.
- Integration tests run when behavior crosses a real external boundary.
- README, architecture, operations, runbooks, reference docs, and ADRs are
  updated when the contract changes.
- The selected quality gate matches the risk.
- The handoff states exactly what was run and what could not run.
