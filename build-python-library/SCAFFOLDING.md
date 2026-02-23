# Project Scaffolding

Templates and patterns for setting up a pip-installable Python library with src layout.

## Contents
- Directory structure
- pyproject.toml template
- __init__.py patterns
- py.typed marker
- Optional dependency groups

## Directory structure

Every project follows this layout exactly:

```
project-name/
├── pyproject.toml
├── README.md
├── src/
│   └── packagename/
│       ├── __init__.py          # Public API only
│       ├── py.typed             # Empty file, marks package as typed
│       ├── _types.py            # Shared types, protocols, dataclasses
│       ├── core.py              # Core logic (framework-agnostic)
│       ├── _internal/           # Private implementation details
│       │   ├── __init__.py
│       │   └── helpers.py
│       └── adapters/            # Framework-specific adapters
│           ├── __init__.py
│           └── framework_name.py
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures
    ├── test_core.py
    ├── test_types.py
    └── adapters/
        ├── __init__.py
        └── test_framework_name.py
```

Rules:
- `src/` prefix is mandatory — prevents importing from source instead of installed package
- One test file per source module, mirroring the directory structure
- `_internal/` or `_underscore_prefix` for non-public modules
- `adapters/` directory for all framework-specific code

## pyproject.toml template

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "package-name"
version = "0.1.0"
description = "One-line description"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.10"
dependencies = [
    # Only include dependencies that EVERY user needs
    # Framework-specific deps go in optional-dependencies
]

[project.optional-dependencies]
# One group per framework/integration
langchain = ["langchain-core>=0.3"]
chroma = ["chromadb>=0.5"]
openai = ["openai>=1.0"]
ollama = ["ollama>=0.4"]
# Dev dependencies
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
]
# All optional integrations for testing
all = [
    "package-name[langchain,chroma,openai,ollama,dev]",
]

[tool.hatch.build.targets.wheel]
packages = ["src/packagename"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.pyright]
include = ["src"]
pythonVersion = "3.10"
```

### Key decisions in the template

- **hatchling** as build backend: simple, fast, well-supported. No setup.py needed.
- **requires-python >= 3.10**: enables `X | Y` union types and `match` statements.
- **pytest-asyncio** with `asyncio_mode = "auto"`: async test functions work without `@pytest.mark.asyncio` decorator.
- **pyright** for type checking: stricter than mypy, better error messages.

## __init__.py patterns

### Root __init__.py (public API)

```python
"""Package description — one line."""

from packagename._types import (
    SomeProtocol,
    SomeDataclass,
    SomeEnum,
)
from packagename.core import (
    MainClass,
    main_function,
)

__all__ = [
    "SomeProtocol",
    "SomeDataclass",
    "SomeEnum",
    "MainClass",
    "main_function",
]

__version__ = "0.1.0"
```

Rules:
- `__all__` must list every public name — no more, no less
- Import from internal modules, never re-export transitive dependencies
- `__version__` string matches pyproject.toml version
- No logic in `__init__.py` — only imports and `__all__`

### Adapter __init__.py (lazy imports)

```python
"""Framework adapters — import only the adapter you use."""

# Do NOT import adapters here. Users import directly:
#   from packagename.adapters.langgraph import LangGraphAdapter
#
# This avoids pulling in framework dependencies for users
# who only use one adapter.
```

Adapter `__init__.py` must be empty or contain only a docstring. Never import adapter modules at the package level — this would force all framework dependencies to be installed.

## py.typed marker

Create an empty file at `src/packagename/py.typed`:

```
# This file intentionally left empty.
# Its presence tells type checkers this package provides type information.
```

This is a PEP 561 requirement for packages that ship type annotations.

## Optional dependency groups

### When to make a dependency optional

| Dependency type | Where it goes |
|----------------|---------------|
| Used by every user (hashlib, dataclasses, typing) | `dependencies` in `[project]` |
| Used by one adapter (langchain, chromadb) | `[project.optional-dependencies]` under adapter name |
| Used only for development (pytest, pyright) | `[project.optional-dependencies.dev]` |
| Used only for a specific feature users opt into | `[project.optional-dependencies]` under feature name |

### Lazy import pattern for optional deps

```python
def _get_chromadb():
    """Import chromadb, raising a helpful error if not installed."""
    try:
        import chromadb
        return chromadb
    except ImportError:
        raise ImportError(
            "chromadb is required for the Chroma adapter. "
            "Install it with: pip install packagename[chroma]"
        ) from None
```

Rules:
- Never import optional dependencies at module top level
- Always provide the pip install command in the error message
- Use `from None` to suppress the chained ImportError traceback

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` when importing after `pip install -e .` | Package directory not in `[tool.hatch.build.targets.wheel].packages` | Add `packages = ["src/packagename"]` to pyproject.toml |
| `ImportError` for a module that exists in src/ | Flat layout (package at root) instead of src layout | Move package into `src/` and update pyproject.toml |
| Type checker can't find the package | Missing `py.typed` marker file | Create empty `src/packagename/py.typed` |
| Installing package pulls in all framework deps | Framework imports at top level of __init__.py or core modules | Move framework imports to adapter modules, use lazy import pattern |
| `pytest` can't find tests | `testpaths` not set in pyproject.toml, or tests/ missing __init__.py | Add `testpaths = ["tests"]` to `[tool.pytest.ini_options]` and create `tests/__init__.py` |
| If none of the above | Run `pip install -e ".[dev]" -v` for verbose output and inspect the error. Check that `src/packagename/__init__.py` exists and contains valid Python |
