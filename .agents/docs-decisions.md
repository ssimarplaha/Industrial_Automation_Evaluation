# Docs And Decisions

Precedence for this repository: Siemens extractor docs under `.agents/AGENTS.md`,
`.agents/architecture.md`, `.agents/workflows/extraction.md`, and
`.agents/checklists/refactor_checklist.md` define the current local contract.
Use this reusable docs guidance only when it does not conflict with those files.

Update documentation in the same work as the behavior it describes. Docs are
part of the contract, especially for public APIs, CLIs, configuration,
deployment, operations, and compatibility decisions.

## Where Updates Belong

- Root README: project purpose, quick start, local setup, common commands, and
  links to deeper docs.
- Package README files: package responsibilities, entrypoints, local test
  commands, and package-specific contracts.
- `docs/architecture/`: runtime shape, data flow, ownership boundaries, schema
  ownership, service boundaries, observability, and external systems.
- `docs/operations/`: installation, configuration, secrets, deployment,
  migrations, upgrades, rollback, and local development.
- `docs/runbooks/`: incident response and operator troubleshooting.
- `docs/reference/`: stable command, API, config, schema, and operational
  reference details.
- `docs/decisions/`: durable architecture and compatibility decisions.
- `AGENTS.md` and `.agents/`: internal agent/contributor guidance.

If the repository uses different paths, follow the local structure and keep the
same ownership split.

## ADR Requirement

Important durable changes require an ADR update or a new ADR. Important means
changes to:

- Schemas, migrations, or data ownership.
- Runtime boundaries between services, jobs, packages, tenants, or deployment
  scopes.
- Service contracts, public APIs, config files, environment variables, or
  credential handling.
- CLI behavior, generated file layout, payload formats, or persisted filenames.
- Retry, leasing, batching, dedupe, idempotency, timeout, or backoff semantics.
- Metrics, logs used operationally, health, readiness, status, or admin
  endpoints.
- Deployment model, release artifact shape, service ownership, write paths,
  permissions, or rollback expectations.
- Security model, authentication, authorization, secret storage, or audit
  behavior.

ADRs should record context, decision, and consequences. They should not become
changelogs for routine implementation detail.

## Documentation Quality

- Keep docs accurate, concrete, and current with code.
- Prefer examples that can be copied safely in local development.
- Do not include production secrets, real customer data, private hostnames,
  private paths, or proprietary payloads in reusable examples.
- Distinguish normative requirements from implementation notes.
- Keep operator-facing docs concise and task-oriented.
- Keep internal engineering standards in `AGENTS.md` and `.agents/` rather than
  mixing them into user docs.

## Docs-Only Changes

For docs-only work:

- Check that links resolve.
- Run docs build or site checks when navigation or generated docs change.
- Run whitespace validation such as `git diff --check` when the project is a Git
  checkout.
- Confirm examples still match current commands, config names, and output.
- State when docs describe intended future behavior rather than current
  behavior.
