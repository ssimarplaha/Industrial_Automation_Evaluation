# Security And Secrets

Precedence for this repository: `.agents/AGENTS.md` defines the Siemens
extractor file-handling contract. Use this reusable security guidance only when
it does not conflict with the local PDF, output, audit, and verification rules.

Security-sensitive material must stay out of source, logs, examples, screenshots,
generated files, test fixtures, support bundles, and chat transcripts unless it
has been explicitly sanitized.

## Credentials

- Load secrets through the project's approved secret-management path.
- Do not hardcode tokens, passwords, private keys, certificates, session cookies,
  database URLs, SMTP credentials, API keys, or cloud credentials.
- Keep local development examples synthetic and clearly non-production.
- Prefer secret references, environment variable names, or placeholder values in
  docs.
- Do not print full credential-bearing config in CLI output, logs, exceptions,
  previews, or tests.

## Logs And Observability

- Logs should include stable identifiers and enough context to debug failures
  without exposing secrets.
- Redact authorization headers, cookies, tokens, passwords, connection strings,
  private keys, and personal data unless the project has an explicit safe
  handling policy.
- Avoid high-cardinality or sensitive values in metric labels.
- Treat status endpoints, debug dumps, traces, and support bundles as possible
  disclosure surfaces.

## Fixtures, Examples, And Generated Files

- Use synthetic data in fixtures and docs examples.
- Sanitize real payloads before committing or sharing them.
- Do not commit local previews, screenshots, rendered emails, generated reports,
  exports, or temporary artifacts unless the request explicitly requires a
  tracked fixture.
- Keep generated output deterministic so secret scans and reviews are reliable.
- Add ignore rules for local artifacts that may contain credentials or private
  data.

## Screenshots And Visual Artifacts

- Inspect screenshots, browser captures, terminal output, and rendered previews
  for secrets before sharing or committing.
- Blur or replace private hostnames, usernames, tokens, customer names, account
  IDs, email addresses, and internal URLs.
- Prefer recreating a synthetic scenario over sanitizing a production capture.

## Dependency And Supply Chain

- Add dependencies only when they are justified by correctness, security, or
  maintainability.
- Prefer well-maintained packages with compatible licenses and active security
  support.
- Run dependency audit tooling when dependency files change and tooling exists.
- Treat release artifacts, checksums, provenance, and package data as part of
  the production security boundary.

## Incident Handling

- If a secret may have been exposed, stop propagating it, remove it from the
  artifact if possible, and report the exposure path.
- Do not claim removal from Git history or external systems unless it was
  actually completed.
- Assume exposed credentials need rotation by the owning operator.
