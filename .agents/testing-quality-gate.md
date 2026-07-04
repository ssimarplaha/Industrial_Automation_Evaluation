# Testing And Quality Gate

Precedence for this repository: `.agents/workflows/extraction.md` defines the
current Siemens test and regeneration commands. Use this file as risk-based
testing guidance only when it does not conflict with that workflow.

Use focused tests while changing code, then run the Siemens gate that matches
the risk.

## Current Siemens Gate

Run the full repo test gate with the bundled runtime:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s src
```

Regenerate outputs only when extraction behavior changes:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/extract_siemens_financials.py
```

After regeneration, the verification report must report `"passed": true`.

## Focused Iteration

Use focused `unittest` runs while implementing when a smaller test target is
clear. Keep paths aligned with the current `src/` test layout.

## Full Gate Expectations

The current Siemens gate covers the maintained unit and hygiene tests. A future
single-command quality gate could add:

- Formatting checks.
- Linting.
- Type checking.
- Unit tests.
- Integration tests when behavior crosses external-system boundaries.
- Coverage reporting with an agreed threshold.
- Wheel or package build.
- Install smoke tests for imports, console scripts, and packaged resources.
- Dependency vulnerability audit.
- Python compile checks.
- Docs/link validation when docs or navigation change.
- Whitespace validation such as `git diff --check` when the project is a Git
  checkout.

Those items are future tooling improvements unless this repo adds them
deliberately.

## Risk-Based Test Selection

- Pure logic change: focused unit tests plus lint/type checks for touched code.
- Public API, CLI, config, or generated output change: add compatibility or
  golden-output tests; run package/install smoke checks only if packaging
  tooling exists.
- Schema or migration change: test forward migration, idempotency where
  required, rollback or compatibility assumptions, and failure reporting.
- Transactional persistence change: test commit, rollback, partial failure, and
  repeated processing.
- Retry, queue, or external call change: test timeout, retry, dead-letter or
  recovery behavior, duplicate delivery, and idempotency.
- Operations or deployment change: test rendering, dry-run behavior, health
  checks, permissions/write paths, and rollback documentation.
- Docs-only change: run whitespace and link checks, plus docs build checks when
  navigation, generated docs, or examples change.

## Coverage

- Coverage should protect important behavior, not reward shallow assertions.
- Add regression tests for bugs before or with the fix.
- Prefer tests of public behavior over tests that freeze private implementation
  details.
- Use integration tests when correctness depends on real database, queue,
  filesystem permission, subprocess, packaging, or service behavior.

## Handoff

Before handoff, report:

- Commands run.
- Commands that failed or could not run.
- Any environment limitation, missing dependency, or sandbox limitation.
- Residual risk if the full gate was not run.

Do not imply a gate passed if it was not executed.
