# ADR 0002: Development Tooling and Standards

Status: Accepted
Date: 2026-01-08

## Context

To improve developer productivity, maintain code quality, and ensure consistency during the rewrite phase, we need a modern linting/formatting tool and a robust testing framework.

## Options Considered

### Linting & Formatting
1) Ruff
   - Pros: Extremely fast, combines many tools (Flake8, isort, Black-compatible formatter), highly configurable via pyproject.toml.
   - Cons: Newer tool, though already very stable and widely adopted.

2) Flake8 + Black + isort
   - Pros: Industry standard for years.
   - Cons: Multiple tools to configure and run, slower than Ruff.

### Testing
1) pytest
   - Pros: Powerful, flexible, standard for modern Python projects, great ecosystem (pytest-django, pytest-cov).
   - Cons: Slight learning curve if coming from unittest.

2) unittest (Django default)
   - Pros: Built into Python/Django.
   - Cons: More boilerplate, fewer features than pytest.

## Decision

Adopt **Ruff** for linting/formatting and **pytest** for testing.

Rationale:
- Ruff provides a single, extremely fast tool for linting, formatting, and import sorting, reducing the overhead of maintaining multiple configurations.
- pytest simplifies test writing and provides better diagnostic information when tests fail.

## Consequences

- Added `pyproject.toml` to the root for Ruff configuration.
- Configured Ruff with a generous line length of 120 and Django-specific rules.
- Added `requirements-dev.txt` including `ruff`, `pytest`, and `pytest-django`.
- Existing `pytest.ini` is used and will be maintained.
- Developers should run `ruff check .` and `ruff format .` before committing.
- New tests should be written using pytest fixtures and patterns where appropriate.

## Follow-up Actions

- [x] Create `pyproject.toml`.
- [x] Create `requirements-dev.txt`.
- [ ] Migrate existing tests to pytest style where beneficial (long term).
- [ ] Integrate Ruff/pytest into CI/CD pipeline.
