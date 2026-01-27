# Contributing to amptimal-shared

This document outlines the standards and process for contributing to the shared library.

## CI/CD Requirements

All PRs must pass the following checks before merge:

| Check | Command | Requirement |
|-------|---------|-------------|
| Tests | `pytest` | All tests pass |
| Linting | `ruff check src/ tests/` | No errors |
| Type checking | `mypy src/amptimal_shared` | No errors |
| Coverage | `pytest --cov` | Minimum 80% |

The CI workflow runs these checks across Python 3.9, 3.10, and 3.11.

## Code Standards

### Type Hints

All functions must have complete type annotations:

```python
def calculate_backoff(
    attempt: int,
    base_seconds: float = 1.0,
    max_backoff_seconds: float = 300.0,
) -> float:
    """Calculate exponential backoff delay."""
    ...
```

### Docstrings

All public functions and classes must have docstrings:

```python
def setup_logging(
    name: str,
    level: str | None = None,
    json_format: bool | None = None,
) -> logging.Logger:
    """
    Configure and return a logger with structured output.

    Args:
        name: Logger name (typically service name)
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to LOG_LEVEL env var.
        json_format: Use JSON output. Defaults to LOG_FORMAT env var.

    Returns:
        Configured logger instance.
    """
    ...
```

### Test Coverage

- Minimum 80% code coverage required
- All new utilities must have corresponding tests
- Test files go in `tests/` with naming pattern `test_<module>.py`

## Adding a New Utility Module

Follow this process when adding new shared functionality:

### 1. Create the module

Create a new file in `src/amptimal_shared/`:

```python
# src/amptimal_shared/my_utility.py
"""Description of what this utility does."""

from typing import ...

def my_function(...) -> ...:
    """Docstring with args and returns."""
    ...
```

### 2. Export in `__init__.py`

Add exports to make the utility available at package level:

```python
# src/amptimal_shared/__init__.py
from amptimal_shared.my_utility import my_function

__all__ = [
    # ... existing exports ...
    "my_function",
]
```

### 3. Add tests

Create `tests/test_my_utility.py`:

```python
import pytest
from amptimal_shared import my_function

def test_my_function_basic():
    result = my_function(...)
    assert result == expected

def test_my_function_edge_case():
    ...
```

### 4. Update README.md

Add a usage section with examples:

```markdown
### My Utility

Description of the utility and when to use it.

\`\`\`python
from amptimal_shared import my_function

result = my_function(...)
\`\`\`
```

### 5. Update CHANGELOG.md

Add an entry under `[Unreleased]`:

```markdown
### Added

- **My utility module** (`amptimal_shared.my_utility`)
  - `my_function()` - Brief description
```

### 6. Notify dependent repos

After merge, create issues in repos that might benefit:

- [amptimal-data](https://github.com/drewgray/amptimal-data)
- [claude-pr-reviewer](https://github.com/drewgray/claude-pr-reviewer)

## PR Process

1. Create a feature branch from `main`
2. Make changes following the standards above
3. Run local checks:
   ```bash
   pytest --cov=amptimal_shared --cov-report=term-missing
   ruff check src/ tests/
   mypy src/amptimal_shared
   ```
4. Push and create PR
5. Address review feedback
6. Squash and merge after approval

## Version Bumping

This library uses [Semantic Versioning](https://semver.org/):

- **PATCH** (0.1.x): Bug fixes, documentation updates
- **MINOR** (0.x.0): New features, backward-compatible changes
- **MAJOR** (x.0.0): Breaking changes

### Breaking Change Policy

**Avoid breaking changes whenever possible.** Consumer repos depend on this library's stability.

If a breaking change is absolutely necessary:

1. Discuss in an issue first
2. Bump major version
3. Update CHANGELOG with migration guide
4. Coordinate with all dependent repos before release

### Releasing

1. Update version in `src/amptimal_shared/__init__.py` and `pyproject.toml`
2. Move CHANGELOG entries from `[Unreleased]` to new version section
3. Create GitHub release with tag `vX.Y.Z`
4. CI will automatically build and publish

## Questions?

Open an issue for questions about contributing or architecture decisions.
