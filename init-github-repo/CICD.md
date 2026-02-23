# CI/CD and Project Detection

How to detect project type, generate CI/CD workflows, and create .gitignore files.

## Contents
- Project type detection
- CI/CD workflow templates
- .gitignore templates
- Failure diagnosis

## Project type detection

Check for these files in order. Use the first match:

| File | Language | Package manager | Test command |
|------|----------|----------------|--------------|
| `pyproject.toml` | Python | pip/uv | `pytest` |
| `setup.py` or `setup.cfg` | Python | pip | `pytest` |
| `package.json` | Node.js | npm/yarn/pnpm | `npm test` |
| `Cargo.toml` | Rust | cargo | `cargo test` |
| `go.mod` | Go | go | `go test ./...` |
| `Gemfile` | Ruby | bundler | `bundle exec rake test` |
| `pom.xml` | Java | maven | `mvn test` |
| `build.gradle` or `build.gradle.kts` | Java/Kotlin | gradle | `./gradlew test` |

If no marker file found, ask the user what language the project uses.

### Extracting metadata from pyproject.toml

Read these fields:
- `[project].name` → package name (for badges, PyPI URL)
- `[project].version` → current version
- `[project].license` → license SPDX identifier (for LICENSE file, badge)
- `[project].requires-python` → minimum Python version (for badge, CI matrix)
- `[project].optional-dependencies.dev` → dev dependencies (for CI install command)
- `[build-system].build-backend` → determines install command (`hatchling` → `pip install -e .`, `setuptools` → `pip install -e .`)

### Extracting metadata from package.json

Read these fields:
- `name` → package name
- `version` → current version
- `license` → license SPDX identifier
- `engines.node` → minimum Node version
- `scripts.test` → test command (use this instead of hardcoding `npm test`)
- `scripts.lint` → lint command (add to CI if present)

## CI/CD workflow templates

### Python (pyproject.toml detected)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest -v
```

If `[project].optional-dependencies` has a group named `dev` or `test`, use `pip install -e ".[dev]"`. Otherwise use `pip install -e . && pip install pytest`.

If the project has a `ruff` or `flake8` dependency, add a lint step before tests:

```yaml
      - name: Lint
        run: ruff check .
```

### Node.js (package.json detected)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
```

If `package.json` has a `lint` script, add `- run: npm run lint` before tests.

### Rust (Cargo.toml detected)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
      - name: Run tests
        run: cargo test
      - name: Check formatting
        run: cargo fmt -- --check
      - name: Clippy
        run: cargo clippy -- -D warnings
```

### Go (go.mod detected)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version-file: go.mod
      - name: Run tests
        run: go test ./...
      - name: Vet
        run: go vet ./...
```

## .gitignore templates

### Python

```gitignore
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
.env
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
*.so
```

### Node.js

```gitignore
node_modules/
dist/
.env
.env.local
*.log
coverage/
.cache/
.parcel-cache/
.next/
```

### Rust

```gitignore
/target
Cargo.lock
```

Note: for libraries, `Cargo.lock` is gitignored. For binaries, it is committed.

### Go

```gitignore
/bin
/vendor
*.exe
*.test
*.out
```

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| CI fails on "pip install -e .[dev]" | No `[project.optional-dependencies].dev` group in pyproject.toml | Check pyproject.toml — use the actual group name, or fall back to `pip install -e . && pip install pytest` |
| CI fails on "npm test" | No `test` script in package.json | Check package.json `scripts` — add a test script or use the actual test command |
| CI matrix runs wrong Python versions | `requires-python` specifies a version not in the matrix | Read `requires-python` and set the matrix to include that version and newer |
| GitHub Actions workflow not detected | File not at `.github/workflows/ci.yml` | Verify the directory structure is exactly `.github/workflows/` (not `.github/workflow/` singular) |
| If none of the above | Run `gh run list` after pushing to see if the workflow was picked up, and `gh run view --log` on a failed run to read the error |
