# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of GateFlow seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities.
2. Email your findings to: **security@gateflow.dev**
3. Include the following in your report:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your report within **48 hours**.
- **Assessment**: We will provide an initial assessment within **5 business days**.
- **Resolution**: Critical vulnerabilities will be patched within **7 days**. Non-critical issues will be addressed in the next scheduled release.
- **Disclosure**: We will coordinate with you on public disclosure timing.

### Scope

The following are in scope for security reports:

- **API endpoints** (`/api/assist`, `/api/venue`, `/api/transport/advice`)
- **Input sanitization** bypass in `sanitize_question()`
- **Rate limiting** circumvention in `RateLimiter`
- **Prompt injection** attacks against the LLM phrasing layer
- **Authentication/Authorization** bypass (if applicable)
- **Dependency vulnerabilities** in `requirements.txt`
- **Docker image** security issues
- **CI/CD pipeline** security misconfigurations

### Out of Scope

- Denial of Service (DoS) attacks against the deployed instance
- Social engineering attacks
- Issues in third-party dependencies with existing CVEs (report to upstream maintainers)
- Vulnerabilities requiring physical access

## Security Measures Implemented

GateFlow implements the following security controls:

### Application Security
- **Content Security Policy (CSP)**: `default-src 'self'` enforced via `GateFlowSecurityMiddleware`
- **X-Frame-Options**: `DENY` — prevents clickjacking attacks
- **X-Content-Type-Options**: `nosniff` — prevents MIME type sniffing
- **Referrer-Policy**: `no-referrer` — prevents referrer leakage
- **Strict CORS**: Origin whitelist enforced via FastAPI CORSMiddleware

### Input Validation
- **Prompt Injection Filtering**: `sanitize_question()` strips control characters and enforces length limits
- **Input Length Limits**: All text inputs capped (questions: 1000 chars, locations: 100 chars)
- **Pydantic Schema Validation**: `extra="forbid"` prevents unexpected fields
- **Type-Safe Models**: Full `mypy --strict` compliance

### Rate Limiting
- **Token Bucket Algorithm**: Per-IP rate limiting (20 requests/minute default)
- **Redis Primary + In-Memory Fallback**: Graceful degradation if Redis is unavailable
- **Atomic Lua Script**: Race-condition-free token consumption on Redis

### Infrastructure
- **Multi-Stage Docker Build**: Minimal runtime image with no build tools
- **Non-Root Container Execution**: Application runs as unprivileged user
- **No `eval`/`exec`**: Confirmed absence of dynamic code execution
- **Secret Management**: All secrets via environment variables, `.env` excluded from version control

### Dependency Management
- **Pinned Dependencies**: `requirements.txt` with exact versions
- **GitHub Actions CI**: Automated linting, type checking, and testing on every push
- **Ruff `select = ["ALL"]`**: Strictest possible static analysis rules

## Security Testing

Security-related test coverage includes:
- `tests/unit/test_security.py` — Input sanitization and rate limiter tests
- `tests/integration/` — End-to-end API security header verification
- `tests/accessibility/` — Accessibility compliance validation

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged in this section (with permission).
