# Contributing to GateFlow

Thank you for considering contributing to GateFlow! This guide explains our workflow and standards.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/bhadanevinay/GateFlow---Smart-Stadiums-Tournament-Operations.git
   cd GateFlow---Smart-Stadiums-Tournament-Operations
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Code Standards

- **Linter:** `ruff` with `select = ["ALL"]` (strictest mode)
- **Type Checker:** `mypy --strict` — all functions must have type annotations
- **Docstrings:** `interrogate --fail-under=100` — every public class/function needs a docstring
- **Formatter:** `ruff format` — consistent code formatting
- **Complexity:** `radon cc` — maximum cyclomatic complexity below 10

### Pre-Commit Checks

Before submitting a PR, run:

```bash
ruff check .
ruff format --check .
mypy --strict app/
interrogate -vv app/
pytest --cov=app --cov-branch --cov-fail-under=100
```

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Ensure all pre-commit checks pass with zero errors.
3. Update documentation if your change affects API behavior.
4. Add or update tests to maintain 100% branch coverage.
5. Submit a pull request with a clear description of your changes.

## Architecture Rules

- **API Controllers** (`app/api/`): Define endpoints and coordinate service calls. No business logic.
- **Domain Models** (`app/models/`): Pydantic schemas and dataclasses. No I/O operations.
- **Services** (`app/services/`): Pure business logic, algorithms, and graph traversals.
- **Third-Party Wrappers**: Isolated in thin clients (e.g., `GeminiClient`).

## Reporting Issues

Use GitHub Issues for bugs and feature requests. For security issues, see `SECURITY.md`.
