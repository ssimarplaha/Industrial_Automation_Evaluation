# Principal Engineering Standard

Precedence for this repository: `.agents/AGENTS.md`, `.agents/architecture.md`,
`.agents/workflows/extraction.md`, and
`.agents/checklists/refactor_checklist.md` define the Siemens extractor
contract. Use this file as reusable engineering discipline only when it does
not conflict with those docs.

Aim for practical, readable correctness. Production software handles data,
credentials, operator workflows, migrations, external systems, and support
debugging. Cleverness is less valuable than explicit behavior that can be
tested, reviewed, and operated.

## Core Values

- Correctness first. Preserve data integrity, compatibility, and clear failure
  behavior.
- Clarity over cleverness. Prefer direct control flow, named concepts, and
  explicit contracts.
- Small testable units. Keep pure logic separate from I/O, process state, time,
  randomness, and external services.
- Typed boundaries. Use type hints, schemas, dataclasses, protocol objects, or
  validators where they make contracts harder to misuse.
- Controlled abstractions. Add an abstraction only when it removes real
  duplication, isolates a real boundary, or matches an established local
  pattern.
- Minimal blast radius. Keep edits close to the requested behavior and the
  modules that own it.

## Public Contracts

Treat these as contracts and review them carefully:

- Database schemas, migrations, indexes, and transaction boundaries.
- Public imports, console scripts, CLI flags, exit codes, and command output
  consumed by users or automation.
- Environment variables, config files, generated paths, dry-run plans, and
  default values.
- File formats, payload schemas, message topics, API routes, storage layout, and
  durable queue semantics.
- Retry, leasing, batching, dedupe, timeout, idempotency, and backoff behavior.
- Logs, metrics, health checks, readiness checks, status output, and admin
  endpoints.
- Deployment artifacts, service ownership, write paths, migration sequence, and
  rollback assumptions.

If a change updates one of these contracts, update tests and documentation in
the same work. For durable compatibility or architecture decisions, add or
update an ADR.

## Code Shape

- Prefer existing package patterns and helper APIs over new local conventions.
- Keep functions and classes small enough to test without live external
  dependencies.
- Isolate side effects behind narrow boundaries such as repositories, clients,
  adapters, command handlers, or service objects.
- Make validation happen before mutation where practical.
- Raise specific exceptions when callers can act on the failure.
- Use structured logging through project loggers. Do not add production
  `print()` calls unless the file is an intentional CLI surface.
- Keep generated output deterministic. Stable ordering matters for reviews,
  tests, audit logs, support bundles, and reproducible builds.
- Avoid hidden global state. Prefer explicit configuration, dependency
  injection, and narrow module-level constants.

## Documentation In Code

- Add docstrings for public modules, classes, functions, and methods when
  behavior is not obvious from the signature.
- Use comments for subtle ordering, transaction boundaries, compatibility
  constraints, security-sensitive behavior, and external-system assumptions.
- Do not narrate obvious assignments or restate function names in comments.
- Keep examples generic and safe. Do not encode customer data, production
  hostnames, credential paths, or proprietary payloads into reusable guidance.

## Change Discipline

- Preserve user changes and unrelated worktree state.
- Avoid unrelated rewrites, broad formatting churn, and import churn.
- Keep generated files, lockfiles, snapshots, and fixtures untouched unless they
  are part of the requested change.
- Prefer backwards-compatible evolution. When breaking compatibility is
  required, make the migration path and rollback constraints explicit.
- Record validation honestly. State what was run, what could not run, and what
  residual risk remains.
