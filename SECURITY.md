# Security Policy & Secret Hygiene

InkLoop is designed for secure, auditable AI comic production.

---

## 1. Secret Hygiene Standards

- **Environment-Only Secrets:** Authentication tokens (`MODEL_API_KEY`, `META_API_KEY`) are read strictly from OS environment variables or local, git-ignored `.env` files.
- **Zero Serialization:** API keys are never written to database tables, logs, error traces, or serialized JSON responses.
- **Diagnostics Masking:** The operational diagnostics endpoint (`/api/v1/config/diagnostics`) reports credential presence as `[SET - REDACTED]` or `[NOT SET]`.
- **Zero History Commitment:** Git repositories are scanned before release to ensure no private keys or tokens enter commit history.

---

## 2. Reporting Security Concerns

If you discover a security vulnerability or potential token exposure:
1. Do not open a public issue.
2. Contact the author directly: **Mohamed Gomaa** (`mnile23@gmail.com` / GitHub: [`@mohgomaa-art`](https://github.com/mohgomaa-art)).
3. Include reproduction steps, affected components, and logs with all tokens redacted.
