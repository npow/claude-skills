# Test Runner Detection and Commands

How to detect the project's test runner and construct commands for single-test execution.

## Detection order

Scan the project root for these files. Use the first match:

| File | Runner | Language |
|------|--------|----------|
| `pytest.ini`, `pyproject.toml` with `[tool.pytest]`, `setup.cfg` with `[tool:pytest]`, `conftest.py` | pytest | Python |
| `tox.ini` | tox (wraps pytest usually) | Python |
| `package.json` with `jest` in deps/devDeps or `jest.config.*` | Jest | JavaScript/TypeScript |
| `package.json` with `vitest` in deps/devDeps or `vitest.config.*` | Vitest | JavaScript/TypeScript |
| `package.json` with `mocha` in deps/devDeps or `.mocharc.*` | Mocha | JavaScript/TypeScript |
| `build.gradle` or `build.gradle.kts` with `test` task | Gradle (JUnit) | Java/Kotlin |
| `pom.xml` with `surefire` or `failsafe` plugin | Maven (JUnit) | Java |
| `go.mod` | go test | Go |
| `Cargo.toml` | cargo test | Rust |
| `*.csproj` or `*.sln` | dotnet test | C#/.NET |
| `Gemfile` with `rspec` | RSpec | Ruby |
| `Gemfile` with `minitest` | Minitest | Ruby |

## Command templates

### pytest (Python)

```bash
# Run single test by name
pytest "FILE_PATH::TEST_NAME" -v --tb=short 2>&1

# Run single test N times
for i in $(seq 1 N); do echo "--- Run $i ---"; pytest "FILE_PATH::TEST_NAME" -v --tb=short 2>&1; echo "EXIT: $?"; done

# Run single test with full suite loaded (ordering test)
pytest --co -q 2>&1 | head -5  # list tests to confirm suite discovery
pytest -v --tb=short 2>&1       # run full suite

# Run specific tests in order
pytest "TEST_A" "TEST_B" "TARGET_TEST" -v --tb=short 2>&1

# Run with timing
pytest "FILE_PATH::TEST_NAME" -v --tb=short --durations=0 2>&1

# Run with verbose setup/teardown
pytest "FILE_PATH::TEST_NAME" -v --tb=long --setup-show 2>&1

# Randomize order (if pytest-randomly installed)
pytest -p randomly --randomly-seed=SEED -v 2>&1
```

### Jest (JavaScript/TypeScript)

```bash
# Run single test by name
npx jest --testNamePattern="TEST_NAME" --verbose 2>&1

# Run single test file
npx jest FILE_PATH --verbose 2>&1

# Run N times
for i in $(seq 1 N); do echo "--- Run $i ---"; npx jest --testNamePattern="TEST_NAME" --verbose 2>&1; echo "EXIT: $?"; done

# Run in band (no parallelism) to check for race conditions
npx jest FILE_PATH --runInBand --verbose 2>&1

# Run with specific test file ordering
npx jest FILE_A FILE_B TARGET_FILE --verbose 2>&1

# Show timing
npx jest FILE_PATH --verbose --detectOpenHandles 2>&1
```

### Vitest (JavaScript/TypeScript)

```bash
# Run single test
npx vitest run FILE_PATH -t "TEST_NAME" 2>&1

# Run N times
for i in $(seq 1 N); do echo "--- Run $i ---"; npx vitest run FILE_PATH -t "TEST_NAME" 2>&1; echo "EXIT: $?"; done

# Run sequentially (disable threads)
npx vitest run FILE_PATH --pool=forks --poolOptions.forks.singleFork 2>&1
```

### Gradle / JUnit (Java/Kotlin)

```bash
# Run single test
./gradlew test --tests "FULLY_QUALIFIED_CLASS.TEST_METHOD" --info 2>&1

# Run N times (Gradle)
for i in $(seq 1 N); do echo "--- Run $i ---"; ./gradlew test --tests "FULLY_QUALIFIED_CLASS.TEST_METHOD" --info 2>&1; echo "EXIT: $?"; done

# Force re-run (no cache)
./gradlew test --tests "FULLY_QUALIFIED_CLASS.TEST_METHOD" --no-build-cache --rerun-tasks 2>&1

# Run full test suite
./gradlew test --info 2>&1
```

### Maven / JUnit (Java)

```bash
# Run single test
mvn test -Dtest="CLASS#METHOD" -pl MODULE 2>&1

# Run N times
for i in $(seq 1 N); do echo "--- Run $i ---"; mvn test -Dtest="CLASS#METHOD" -pl MODULE 2>&1; echo "EXIT: $?"; done

# Force re-run
mvn test -Dtest="CLASS#METHOD" -pl MODULE -Dmaven.test.failure.ignore=false 2>&1
```

### go test (Go)

```bash
# Run single test
go test -run "TEST_NAME" -v ./PACKAGE/ 2>&1

# Run N times
go test -run "TEST_NAME" -v -count=N ./PACKAGE/ 2>&1

# Run with race detector
go test -run "TEST_NAME" -v -race ./PACKAGE/ 2>&1

# Run with timeout
go test -run "TEST_NAME" -v -timeout 30s ./PACKAGE/ 2>&1

# Shuffle order
go test -v -shuffle=on ./PACKAGE/ 2>&1
```

### cargo test (Rust)

```bash
# Run single test
cargo test TEST_NAME -- --exact --nocapture 2>&1

# Run N times
for i in $(seq 1 N); do echo "--- Run $i ---"; cargo test TEST_NAME -- --exact --nocapture 2>&1; echo "EXIT: $?"; done

# Run single-threaded
cargo test TEST_NAME -- --exact --nocapture --test-threads=1 2>&1
```

### RSpec (Ruby)

```bash
# Run single test
bundle exec rspec FILE_PATH:LINE_NUMBER 2>&1

# Run N times
for i in $(seq 1 N); do echo "--- Run $i ---"; bundle exec rspec FILE_PATH:LINE_NUMBER 2>&1; echo "EXIT: $?"; done

# Run with random order and seed
bundle exec rspec --order rand:SEED 2>&1
```

### dotnet test (C#/.NET)

```bash
# Run single test
dotnet test --filter "FullyQualifiedName~TEST_NAME" --verbosity normal 2>&1

# Run N times
for i in $(seq 1 N); do echo "--- Run $i ---"; dotnet test --filter "FullyQualifiedName~TEST_NAME" --verbosity normal 2>&1; echo "EXIT: $?"; done
```

## Parsing exit codes

All runners use exit code conventions:
- `0` = all tests passed
- `1` or non-zero = at least one test failed
- `2` (pytest) = test collection error (wrong test path or syntax error)

When parsing multi-run output, count exits by grepping for `EXIT: 0` (pass) vs `EXIT: [^0]` (fail).
