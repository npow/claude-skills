---
name: build-python-library
description: Implements pip-installable Python libraries from scratch using src layout, pyproject.toml, and pytest. Use when the user asks to build, create, implement, or scaffold a Python library, package, pip package, middleware, SDK, or wrapper. Covers project scaffolding, proxy/wrapper patterns, provider-agnostic interfaces, async/sync support, and test infrastructure.
---

# Build Python Library

Implements pip-installable Python libraries by scaffolding the project structure, building core abstractions with adapters, and verifying each module with pytest before proceeding.

## Workflow

1. **Scaffold the project** — create src layout, pyproject.toml, package structure, and py.typed marker. See [SCAFFOLDING.md](SCAFFOLDING.md).
2. **Define the public API** — write `__init__.py` with explicit exports and `__all__`. Only types and functions users need. See [SCAFFOLDING.md](SCAFFOLDING.md).
3. **Implement core abstractions** — build protocols/ABCs, data classes, and shared types that all concrete implementations depend on. See [PATTERNS.md](PATTERNS.md).
4. **Test core abstractions** — write pytest tests for core types and protocols. Run `pytest` and verify zero failures before proceeding. See [TESTING.md](TESTING.md).
5. **Implement concrete modules** — build one module at a time (proxy wrappers, provider clients, adapters). See [PATTERNS.md](PATTERNS.md).
6. **Test each module before the next** — write tests for the module just implemented. Run `pytest` and verify zero failures before starting the next module. See [TESTING.md](TESTING.md).
7. **Install and verify** — run `pip install -e ".[dev]"` and verify the package imports correctly from a clean script. See [TESTING.md](TESTING.md).
8. **Run full test suite** — run `pytest -v` and verify all tests pass, then run `python -c "from packagename import ..."` to verify public API. See [TESTING.md](TESTING.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] Project uses src layout: `src/packagename/` not `packagename/` at root
- [ ] `pyproject.toml` exists with `[build-system]`, `[project]`, and `[project.optional-dependencies]`
- [ ] `py.typed` marker file exists in the package directory
- [ ] `__init__.py` has explicit `__all__` listing only public names
- [ ] Every public function and class has a type-hinted signature (all parameters and return type)
- [ ] Every module has a corresponding test file (`src/pkg/foo.py` → `tests/test_foo.py`)
- [ ] `pytest -v` passes with zero failures
- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `python -c "from packagename import ..."` imports all public API names without error
- [ ] No third-party imports in core modules that lack a corresponding optional dependency group
- [ ] Proxy/wrapper classes delegate unknown attributes via `__getattr__` to the wrapped object

## Golden rules

Hard rules. Never violate these.

1. **Src layout always.** Every project uses `src/packagename/` structure. Never place the package at the repository root. This prevents accidental imports from the source directory instead of the installed package.
2. **Test before you proceed.** Never implement module N+1 until module N has passing tests. Run `pytest` after each module. This catches integration errors early instead of at the end.
3. **Explicit public API.** `__init__.py` must define `__all__` and import only the names users need. Internal modules start with underscore (`_internal.py`) or live in a `_private/` subdirectory. Never expose implementation details.
4. **Type hints on every signature.** Every function parameter and return type must have a type annotation. Use `Protocol` for duck-typed interfaces, not `ABC` unless you need shared implementation.
5. **Optional dependencies in extras.** Third-party framework imports (langchain, chromadb, openai) must be in `[project.optional-dependencies]` groups and imported lazily with try/except at usage point, not at module top level.
6. **Proxy delegates everything.** Wrapper classes must implement `__getattr__` to forward unknown attribute access to the wrapped object. Never enumerate and re-implement every method — the proxy must work with future methods the wrapped library adds.

## Reference files

| File | Contents |
|------|----------|
| [SCAFFOLDING.md](SCAFFOLDING.md) | Project structure template, pyproject.toml template, __init__.py patterns, py.typed setup |
| [PATTERNS.md](PATTERNS.md) | Proxy/wrapper pattern, provider-agnostic interfaces, async/sync dual support, lazy imports |
| [TESTING.md](TESTING.md) | pytest configuration, fixture patterns, mocking external services, test-per-module workflow, install verification |
