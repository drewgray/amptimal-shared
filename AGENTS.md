# AGENTS.md - Agent Operating Instructions

## Default Operating Mode

This is a **shared library** repository. Changes here affect multiple downstream services.

**Priority:** Stability over features. All changes must maintain backward compatibility unless coordinated across consumer repos.

## New Session Checklist

1. Read `CLAUDE.md` for quick reference
2. Read `README.md` for full API documentation
3. Check `CHANGELOG.md` for recent changes
4. Review `CONTRIBUTING.md` for standards

## Repository Layout

```
amptimal-shared/
├── src/amptimal_shared/
│   ├── __init__.py      # Package exports, __version__
│   ├── logging.py       # Structured logging utilities
│   ├── health.py        # Health server with Prometheus metrics
│   ├── retry.py         # Exponential backoff retry logic
│   └── config.py        # Pydantic base settings
├── tests/
│   ├── test_logging.py
│   ├── test_health.py
│   ├── test_retry.py
│   └── test_config.py
├── .github/workflows/
│   ├── test.yml         # CI: pytest, ruff, mypy
│   └── publish.yml      # Release: build and publish
├── pyproject.toml       # Dependencies, tool config
├── README.md            # Full documentation
├── CLAUDE.md            # AI quick reference
├── AGENTS.md            # This file
├── CHANGELOG.md         # Version history
└── CONTRIBUTING.md      # Contribution guidelines
```

## Task Workflows

### Adding a New Utility Module

**Trigger:** Request to add shared functionality (e.g., "add a caching utility")

**Steps:**

1. **Create module file**
   ```
   src/amptimal_shared/<utility_name>.py
   ```
   - Add module docstring
   - Implement with full type hints
   - Add docstrings to all public functions/classes

2. **Export in `__init__.py`**
   - Import the public API
   - Add to `__all__` list

3. **Create test file**
   ```
   tests/test_<utility_name>.py
   ```
   - Test happy path
   - Test edge cases
   - Test error conditions
   - Aim for >80% coverage

4. **Update documentation**
   - Add usage section to `README.md`
   - Add entry to `CHANGELOG.md` under `[Unreleased]`

5. **Run all checks**
   ```bash
   ruff check src/ tests/
   mypy src/amptimal_shared --ignore-missing-imports
   pytest --cov=amptimal_shared --cov-report=term-missing
   ```

6. **Create PR** with description of:
   - What the utility does
   - Why it belongs in shared library
   - Which consumer repos will use it

### Fixing a Bug

**Trigger:** Bug report or failing test

**Steps:**

1. **Reproduce the issue**
   - Write a failing test if one doesn't exist
   - Understand the root cause

2. **Implement fix**
   - Make minimal changes
   - Don't refactor unrelated code

3. **Verify fix**
   ```bash
   pytest tests/test_<affected_module>.py -v
   pytest --cov=amptimal_shared
   ```

4. **Update CHANGELOG.md**
   - Add entry under `[Unreleased]` > `### Fixed`

5. **Run all checks before PR**

### Updating an Existing Module

**Trigger:** Feature request or enhancement

**Steps:**

1. **Check backward compatibility**
   - Can existing callers work unchanged?
   - Are default values preserved?
   - Are return types consistent?

2. **Update implementation**
   - Add new parameters with defaults
   - Extend, don't replace

3. **Update tests**
   - Add tests for new functionality
   - Ensure existing tests still pass

4. **Update documentation**
   - Update `README.md` examples if API changed
   - Add `CHANGELOG.md` entry under `### Changed` or `### Added`

5. **Run all checks**

### Releasing a New Version

**Trigger:** Ready to release accumulated changes

**Steps:**

1. **Determine version bump**
   - PATCH (0.1.x): Bug fixes only
   - MINOR (0.x.0): New features, backward compatible
   - MAJOR (x.0.0): Breaking changes (coordinate with consumers first)

2. **Update version in two places**
   - `src/amptimal_shared/__init__.py`: `__version__ = "X.Y.Z"`
   - `pyproject.toml`: `version = "X.Y.Z"`

3. **Update CHANGELOG.md**
   - Move `[Unreleased]` items to new version section
   - Add date: `## [X.Y.Z] - YYYY-MM-DD`
   - Add compare link at bottom

4. **Create PR, merge to main**

5. **Create GitHub release**
   - Tag: `vX.Y.Z`
   - Title: `vX.Y.Z`
   - Body: Copy from CHANGELOG

6. **Notify consumer repos** (if significant changes)

## Quick Commands Reference

| Task | Command |
|------|---------|
| Install dev | `pip install -e ".[dev]"` |
| Run tests | `pytest` |
| Run tests verbose | `pytest -v` |
| Run single test file | `pytest tests/test_health.py` |
| Run with coverage | `pytest --cov=amptimal_shared --cov-report=term-missing` |
| Lint | `ruff check src/ tests/` |
| Lint fix | `ruff check src/ tests/ --fix` |
| Type check | `mypy src/amptimal_shared --ignore-missing-imports` |
| All checks | `ruff check src/ tests/ && mypy src/amptimal_shared --ignore-missing-imports && pytest` |

## Integration Points

### Consumer Repos

| Repo | Services | Primary Usage |
|------|----------|---------------|
| amptimal-data | 7+ microservices | All modules |
| claude-pr-reviewer | 2 services | logging, health, config |

### How Consumers Install

```bash
# In consumer repo requirements.txt or pyproject.toml
pip install git+https://github.com/drewgray/amptimal-shared.git

# Pin to specific version
pip install git+https://github.com/drewgray/amptimal-shared.git@v0.1.0
```

### Breaking Change Coordination

If a breaking change is necessary:

1. Create issue in this repo describing the change
2. Create issues in all consumer repos
3. Coordinate migration timing
4. Bump major version
5. Include migration guide in CHANGELOG

## Testing Requirements

- All new code must have tests
- Minimum 80% coverage
- Tests must pass on Python 3.9, 3.10, 3.11
- Use `pytest-asyncio` for async tests
- Use `httpx` for HTTP client testing

### Test File Naming

```
tests/test_<module_name>.py
```

### Common Test Patterns

```python
# Fixtures
@pytest.fixture
def sample_settings():
    return MySettings(...)

# Async tests (auto mode enabled)
async def test_async_function():
    result = await my_async_fn()
    assert result == expected

# Parametrized tests
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
])
def test_with_params(input, expected):
    assert double(input) == expected
```
