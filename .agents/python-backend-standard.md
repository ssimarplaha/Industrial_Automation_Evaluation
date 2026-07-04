# Python Backend Standard

Precedence for this repository: `.agents/AGENTS.md` and
`.agents/workflows/extraction.md` define the current Siemens runtime, test, and
regeneration commands. Use this file as reusable Python guidance only when it
does not conflict with those docs.

## Runtime And Project Shape

- Use the bundled Python runtime command in `.agents/workflows/extraction.md`
  when local Python lacks extractor dependencies.
- Keep the current `src/` layout: package code under `src/siemens_extractor/`,
  the compatibility wrapper at `src/extract_siemens_financials.py`, and tests
  under `src/`.
- Keep runtime dependencies in the current repo files unless project metadata
  is deliberately introduced.
- Preserve the script entrypoint unless the user asks for packaging changes.
- Keep runtime dependencies and development dependencies separated.
- Lock production/runtime dependencies if deployment repeatability becomes a
  project requirement.

## Imports And Startup

- Imports must be side-effect-light. Importing a module should not require
  secrets, network access, database connections, queue connections, filesystem
  mutation, thread startup, service startup, or environment-specific paths.
- Put environment loading in explicit config factories such as `from_env()`, not
  at package import time.
- Put external connections in explicit client, repository, or service startup
  methods.
- Keep CLI parsing and process setup near entrypoints. Keep business logic
  importable and testable without running the process.
- Avoid circular imports by keeping shared types, schemas, and utilities in
  narrow modules with no runtime side effects.

## Typing

- Type public functions, methods, dataclasses, protocols, and complex return
  values.
- Prefer precise built-in generics such as `list[str]`, `dict[str, int]`, and
  `Path` over loose `Any` or stringly typed paths.
- Use `TypedDict`, dataclasses, pydantic models, or explicit validators for
  structured data when the shape is a contract.
- Static type checking is a future tooling improvement unless this repo adds
  that gate deliberately.
- Do not silence type errors broadly. Narrow ignores to specific lines and keep
  the reason obvious.

## Formatting And Linting

- Follow the style of nearby code and keep formatting churn scoped.
- Dedicated formatter and linter configuration is a future tooling improvement
  unless this repo adds it deliberately.
- If a formatter or linter is introduced later, do not reformat unrelated files
  merely because the tool is available.
- Prefer the standard library unless a dependency clearly improves correctness,
  security, or maintainability.

## Error Handling And Logging

- Raise specific exceptions or return explicit result types when callers need to
  distinguish failure modes.
- Preserve original exception context with `raise ... from exc` when wrapping
  lower-level failures.
- Use structured logging for production behavior. Include stable identifiers and
  state needed for debugging, but never secrets or full credential-bearing
  config.
- Make retries, timeouts, and backoff explicit at external boundaries.
- Make idempotency keys and dedupe identifiers deterministic where repeated
  processing is possible.

## Package And Build Hygiene

- Package builds, install smoke tests, and console-script checks are future
  tooling improvements unless this repo adds packaging deliberately.
- Keep generated artifacts out of source unless they are canonical fixtures,
  release assets, or the current tracked Siemens outputs.
- Run compile checks for broad Python changes when the environment supports
  them.
- Keep modules cohesive. Split files when they become hard to review or test;
  use any project-specific file-length guardrail if one exists.

## Testing Defaults

- The current Siemens gate is `unittest discover -s src` with the bundled
  runtime shown in `.agents/workflows/extraction.md`.
- pytest is a future tooling improvement unless this repo adopts it
  deliberately.
- Mark optional live integration tests separately if such tests are introduced.
- Keep focused tests close to the behavior being changed.
- Add regression tests for compatibility bugs, parsing/routing changes, config
  rendering, retries, transactions, and generated output.
- Use temporary directories, fake clients, and local fixtures instead of live
  services for unit tests.
