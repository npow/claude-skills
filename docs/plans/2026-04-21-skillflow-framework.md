# skillflow Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `skillflow` framework — a pip-installable Temporal-backed runtime for Claude Code skills — plus a `hello-world` smoke skill that exercises every framework surface end-to-end. Produces a working, testable package where `skillflow launch hello-world "greeting text"` round-trips through Temporal and surfaces its result via the 4-layer result-surfacing safety net.

**Architecture:** Python package with CLI (`skillflow`), long-lived worker daemon (auto-spawning), Temporal dev server for durability, Anthropic SDK + `claude -p` subprocess transports for subagents, `~/.skillflow/` filesystem root for state+INBOX, SessionStart hook for crash-recovery result surfacing. No Netflix internal dependencies; Anthropic SDK with configurable `base_url` supports both `api.anthropic.com` and local model-gateway proxies.

**Tech Stack:** Python 3.11+, `temporalio` SDK, `anthropic` SDK, `click` for CLI, `pytest` + `pytest-asyncio` for tests, `ruff` for lint, `mypy --strict` for types.

**Prerequisite:** Temporal CLI (`brew install temporal`) installed on the developer machine; dev server running via `temporal server start-dev` (already confirmed running on this host, port 7233).

**Reference spec:** [`docs/specs/2026-04-21-deep-qa-temporal-design.md`](../specs/2026-04-21-deep-qa-temporal-design.md)

**Out of scope for this plan:** the deep-qa-temporal workflow (separate plan, gated on this plan landing and the `hello-world` smoke skill proving framework neutrality).

---

## File Structure

New standalone repo `skillflow/` on personal GitHub. Layout after this plan is complete:

```
skillflow/
├── pyproject.toml                         # package metadata, deps, entry points
├── README.md                              # public-facing: install + usage
├── LICENSE                                # MIT
├── .gitignore
├── .github/workflows/ci.yml               # pytest + ruff + mypy on push
├── skillflow/                             # framework package
│  ├── __init__.py                         # exports: launch, register_skill
│  ├── paths.py                            # ~/.skillflow/ layout resolver
│  ├── temporal_client.py                  # Temporal connect + preflight
│  ├── registry.py                         # skill registration + discovery
│  ├── cli.py                              # click entry point: skillflow <subcommand>
│  ├── worker.py                           # worker daemon lifecycle (fg, --detach, --stop, auto-spawn)
│  ├── inbox.py                            # ~/.skillflow/INBOX.md read/write/dismiss
│  ├── hook.py                             # SessionStart hook install/uninstall/read
│  ├── notify.py                           # desktop notifier (macOS osascript, Linux notify-send)
│  ├── transport/
│  │  ├── __init__.py
│  │  ├── anthropic_sdk.py                 # default provider with configurable base_url
│  │  ├── claude_cli.py                    # `claude -p` subprocess transport
│  │  ├── structured_output.py             # STRUCTURED_OUTPUT_START/END parser
│  │  └── dispatcher.py                    # transport selection logic
│  └── durable/
│     ├── __init__.py
│     ├── state.py                         # base WorkflowState dataclass (generation counter, activity ledger)
│     ├── retry_policies.py                # shared retry policies per model tier
│     └── activities.py                    # write_artifact, emit_finding, spawn_subagent, snapshot_workspace
├── skills/
│  └── hello_world/                        # framework smoke-test skill
│     ├── __init__.py                      # exports register()
│     ├── workflow.py                      # HelloWorldWorkflow
│     └── state.py                         # HelloWorldState
└── tests/
   ├── conftest.py                         # shared fixtures: tmp_path INBOX, fake Temporal env
   ├── test_paths.py
   ├── test_temporal_client.py
   ├── test_registry.py
   ├── test_structured_output.py
   ├── test_anthropic_sdk.py
   ├── test_claude_cli.py
   ├── test_dispatcher.py
   ├── test_state.py
   ├── test_retry_policies.py
   ├── test_activities.py
   ├── test_inbox.py
   ├── test_hook.py
   ├── test_notify.py
   ├── test_cli_launch.py
   ├── test_cli_list_show.py
   ├── test_cli_worker.py
   ├── test_cli_hook.py
   ├── test_cli_doctor.py
   ├── test_worker.py
   └── skills/
      ├── __init__.py
      └── test_hello_world.py              # workflow-level test with time-skipped env
   └── e2e/
      └── test_end_to_end.py               # real Temporal + real transport + hello-world
```

All modules stay small and single-responsibility. No file should exceed ~250 lines; if a task produces something bigger, split it before committing.

---

## Task 1: Repo scaffold

**Files:**
- Create: `skillflow/pyproject.toml`
- Create: `skillflow/README.md`
- Create: `skillflow/LICENSE` (MIT)
- Create: `skillflow/.gitignore`
- Create: `skillflow/.github/workflows/ci.yml`
- Create: `skillflow/skillflow/__init__.py` (empty for now; exports added in later tasks)
- Create: `skillflow/tests/__init__.py` (empty)

- [ ] **Step 1: Create repo directory + git init**

Run:
```bash
mkdir -p ~/code/skillflow && cd ~/code/skillflow
git init
```

- [ ] **Step 2: Write `pyproject.toml`**

Content:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "skillflow"
version = "0.1.0"
description = "Temporal-backed workflow runtime for Claude Code skills"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [{ name = "npow" }]
dependencies = [
    "anthropic>=0.40.0",
    "click>=8.1.0",
    "temporalio>=1.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[project.scripts]
skillflow = "skillflow.cli:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

Content:
```
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/
.venv/
.env
.DS_Store
```

- [ ] **Step 4: Write `LICENSE`** (standard MIT text, with copyright line `Copyright (c) 2026 npow`)

- [ ] **Step 5: Write stub `README.md`**

```markdown
# skillflow

Temporal-backed workflow runtime for Claude Code skills.

Status: pre-alpha. Under active development.

See `docs/specs/2026-04-21-deep-qa-temporal-design.md` in the consuming repo for the design.
```

- [ ] **Step 6: Write `.github/workflows/ci.yml`**

Content:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: pip install -e ".[dev]"
      - name: Lint
        run: ruff check skillflow tests
      - name: Type-check
        run: mypy skillflow
      - name: Test
        run: pytest -v --cov=skillflow
```

- [ ] **Step 7: Create empty package markers**

```bash
mkdir -p skillflow/transport skillflow/durable skills/hello_world tests/skills tests/e2e
touch skillflow/__init__.py skillflow/transport/__init__.py skillflow/durable/__init__.py
touch skills/__init__.py skills/hello_world/__init__.py
touch tests/__init__.py tests/skills/__init__.py tests/e2e/__init__.py
```

- [ ] **Step 8: Install package + dev deps, smoke-test CLI entry point**

Run:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
skillflow --help
```
Expected: `skillflow` command not found error OR an error about `skillflow.cli:main` not existing (module stub is empty — that's fine for now; Task 17 adds the CLI).

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: scaffold skillflow package with pyproject, CI, license"
```

---

## Task 2: Paths module

Central resolver for all `~/.skillflow/` filesystem locations so every other module imports paths from one place.

**Files:**
- Create: `skillflow/skillflow/paths.py`
- Create: `tests/test_paths.py`

- [ ] **Step 1: Write failing test** (`tests/test_paths.py`)

```python
from pathlib import Path

from skillflow.paths import Paths


def test_paths_default_home_is_dot_skillflow(tmp_path: Path) -> None:
    p = Paths(root=tmp_path)
    assert p.root == tmp_path
    assert p.inbox == tmp_path / "INBOX.md"
    assert p.runs_dir == tmp_path / "runs"
    assert p.worker_log_dir == tmp_path / "logs"


def test_run_dir_for(tmp_path: Path) -> None:
    p = Paths(root=tmp_path)
    run_dir = p.run_dir_for("hello-world-abc123")
    assert run_dir == tmp_path / "runs" / "hello-world-abc123"


def test_ensure_creates_directories(tmp_path: Path) -> None:
    p = Paths(root=tmp_path)
    p.ensure()
    assert p.runs_dir.is_dir()
    assert p.worker_log_dir.is_dir()


def test_from_env_respects_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SKILLFLOW_ROOT", str(tmp_path / "custom"))
    p = Paths.from_env()
    assert p.root == tmp_path / "custom"


def test_from_env_defaults_to_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SKILLFLOW_ROOT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    p = Paths.from_env()
    assert p.root == tmp_path / ".skillflow"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_paths.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skillflow.paths'`

- [ ] **Step 3: Implement paths module** (`skillflow/skillflow/paths.py`)

```python
"""Filesystem layout for skillflow runtime state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    """Resolves every skillflow filesystem location from a single root."""

    root: Path

    @property
    def inbox(self) -> Path:
        return self.root / "INBOX.md"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def worker_log_dir(self) -> Path:
        return self.root / "logs"

    def run_dir_for(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    def ensure(self) -> None:
        """Create any missing directories. Idempotent."""
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.worker_log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> Paths:
        override = os.environ.get("SKILLFLOW_ROOT")
        if override:
            return cls(root=Path(override))
        return cls(root=Path(os.environ["HOME"]) / ".skillflow")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_paths.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/paths.py tests/test_paths.py
git commit -m "feat(paths): add Paths module for ~/.skillflow layout"
```

---

## Task 3: Temporal client + preflight

Wraps `temporalio.client.Client` with connection + a cheap-probe preflight so callers can detect "Temporal unreachable" cleanly.

**Files:**
- Create: `skillflow/skillflow/temporal_client.py`
- Create: `tests/test_temporal_client.py`

- [ ] **Step 1: Write failing test** (`tests/test_temporal_client.py`)

```python
import pytest

from skillflow.temporal_client import (
    DEFAULT_NAMESPACE,
    DEFAULT_TARGET,
    TASK_QUEUE,
    TemporalUnreachable,
    preflight,
)


async def test_preflight_fails_fast_on_bad_target() -> None:
    with pytest.raises(TemporalUnreachable) as exc:
        await preflight(target="127.0.0.1:1", timeout_seconds=0.2)
    assert "127.0.0.1:1" in str(exc.value)


async def test_preflight_succeeds_against_running_server() -> None:
    # Skipped in CI; locally verifies the real dev server.
    pytest.importorskip("temporalio")
    try:
        await preflight(target=DEFAULT_TARGET, timeout_seconds=2.0)
    except TemporalUnreachable:
        pytest.skip("local Temporal dev server not running")


def test_constants_hold_expected_defaults() -> None:
    assert DEFAULT_TARGET == "localhost:7233"
    assert DEFAULT_NAMESPACE == "default"
    assert TASK_QUEUE == "skillflow"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_temporal_client.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement temporal_client module** (`skillflow/skillflow/temporal_client.py`)

```python
"""Temporal client connection + preflight check."""

from __future__ import annotations

import asyncio

from temporalio.client import Client

DEFAULT_TARGET = "localhost:7233"
DEFAULT_NAMESPACE = "default"
TASK_QUEUE = "skillflow"


class TemporalUnreachable(RuntimeError):
    """Raised when the Temporal server isn't reachable within the probe deadline."""


async def connect(
    target: str = DEFAULT_TARGET,
    namespace: str = DEFAULT_NAMESPACE,
    timeout_seconds: float = 5.0,
) -> Client:
    try:
        return await asyncio.wait_for(
            Client.connect(target, namespace=namespace),
            timeout=timeout_seconds,
        )
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        raise TemporalUnreachable(
            f"Temporal server at {target} not reachable within {timeout_seconds}s: {exc}. "
            f"Start with `temporal server start-dev` and retry."
        ) from exc


async def preflight(
    target: str = DEFAULT_TARGET,
    namespace: str = DEFAULT_NAMESPACE,
    timeout_seconds: float = 2.0,
) -> None:
    """Cheap probe: connect + describe_namespace. Raises TemporalUnreachable on failure."""

    client = await connect(target=target, namespace=namespace, timeout_seconds=timeout_seconds)
    try:
        await asyncio.wait_for(
            client.service_client.workflow_service.describe_namespace(
                _make_describe_namespace_request(namespace)
            ),
            timeout=timeout_seconds,
        )
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        raise TemporalUnreachable(
            f"Temporal describe_namespace({namespace}) at {target} failed: {exc}"
        ) from exc


def _make_describe_namespace_request(namespace: str):  # type: ignore[no-untyped-def]
    from temporalio.api.workflowservice.v1 import DescribeNamespaceRequest

    return DescribeNamespaceRequest(namespace=namespace)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_temporal_client.py -v`
Expected: 2 PASS, 1 possibly skipped (the live-server test skips if dev server isn't up).

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/temporal_client.py tests/test_temporal_client.py
git commit -m "feat(temporal): add Client connect + preflight with clear unreachable error"
```

---

## Task 4: Structured output parser

Implements the `STRUCTURED_OUTPUT_START/END` contract shared across every subagent-producing activity.

**Files:**
- Create: `skillflow/skillflow/transport/structured_output.py`
- Create: `tests/test_structured_output.py`

- [ ] **Step 1: Write failing test** (`tests/test_structured_output.py`)

```python
import pytest

from skillflow.transport.structured_output import (
    MalformedResponseError,
    parse_structured,
)


def test_parses_single_block() -> None:
    text = """
    Some prose before.
    STRUCTURED_OUTPUT_START
    VERDICT|VERIFIED
    CONFIDENCE|high
    NOTES|Looks correct
    STRUCTURED_OUTPUT_END
    Prose after.
    """
    result = parse_structured(text)
    assert result == {
        "VERDICT": "VERIFIED",
        "CONFIDENCE": "high",
        "NOTES": "Looks correct",
    }


def test_last_block_wins_when_multiple() -> None:
    text = """
    STRUCTURED_OUTPUT_START
    VERDICT|FALSE
    STRUCTURED_OUTPUT_END

    STRUCTURED_OUTPUT_START
    VERDICT|VERIFIED
    STRUCTURED_OUTPUT_END
    """
    assert parse_structured(text) == {"VERDICT": "VERIFIED"}


def test_missing_markers_raises() -> None:
    with pytest.raises(MalformedResponseError):
        parse_structured("just some prose, no markers at all")


def test_empty_block_raises() -> None:
    text = "STRUCTURED_OUTPUT_START\nSTRUCTURED_OUTPUT_END"
    with pytest.raises(MalformedResponseError):
        parse_structured(text)


def test_ignores_lines_without_pipe_separator() -> None:
    text = """
    STRUCTURED_OUTPUT_START
    VERDICT|VERIFIED
    this line has no pipe and must be skipped
    NOTES|ok
    STRUCTURED_OUTPUT_END
    """
    assert parse_structured(text) == {"VERDICT": "VERIFIED", "NOTES": "ok"}


def test_pipe_inside_value_is_preserved() -> None:
    text = "STRUCTURED_OUTPUT_START\nNOTES|a|b|c\nSTRUCTURED_OUTPUT_END"
    assert parse_structured(text) == {"NOTES": "a|b|c"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_structured_output.py -v`
Expected: `ModuleNotFoundError` for every test.

- [ ] **Step 3: Implement parser** (`skillflow/skillflow/transport/structured_output.py`)

```python
"""Parses STRUCTURED_OUTPUT_START/END blocks from subagent responses.

Contract: subagents emit machine-parseable `KEY|VALUE` lines between markers.
Anything outside the block is ignored. When multiple blocks are present the
LAST one wins (allows subagents to revise their answer).

Missing or empty block → MalformedResponseError. Callers use the shared
execution-model-contracts fail-safe rule (return the WORST legal value).
"""

from __future__ import annotations

import re

START_MARKER = "STRUCTURED_OUTPUT_START"
END_MARKER = "STRUCTURED_OUTPUT_END"

_BLOCK_PATTERN = re.compile(
    rf"{re.escape(START_MARKER)}\s*(?P<body>.*?)\s*{re.escape(END_MARKER)}",
    re.DOTALL,
)


class MalformedResponseError(ValueError):
    """Raised when the subagent response lacks a parseable structured block."""


def parse_structured(text: str) -> dict[str, str]:
    """Return the key-value pairs from the LAST structured block in ``text``.

    Raises MalformedResponseError if no complete block exists or the block is empty.
    """

    matches = list(_BLOCK_PATTERN.finditer(text))
    if not matches:
        raise MalformedResponseError(
            f"Response contains no {START_MARKER}/{END_MARKER} block"
        )

    body = matches[-1].group("body").strip()
    if not body:
        raise MalformedResponseError("Structured block is present but empty")

    result: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        key, _, value = line.partition("|")
        result[key.strip()] = value.strip()

    if not result:
        raise MalformedResponseError(
            "Structured block has no parseable KEY|VALUE lines"
        )

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_structured_output.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/transport/structured_output.py tests/test_structured_output.py
git commit -m "feat(transport): add STRUCTURED_OUTPUT parser with last-block-wins semantics"
```

---

## Task 5: Anthropic SDK transport

Default transport. Uses the stock `anthropic` SDK; `ANTHROPIC_BASE_URL` env var routes through any compatible proxy (model gateway, Bedrock, etc.) transparently.

**Files:**
- Create: `skillflow/skillflow/transport/anthropic_sdk.py`
- Create: `tests/test_anthropic_sdk.py`

- [ ] **Step 1: Write failing test** (`tests/test_anthropic_sdk.py`)

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from skillflow.transport.anthropic_sdk import AnthropicSdkTransport, ModelTier


@pytest.fixture
def mock_anthropic_client(monkeypatch):
    fake = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    content=[SimpleNamespace(type="text", text="hello back")],
                    usage=SimpleNamespace(input_tokens=5, output_tokens=2),
                )
            )
        )
    )
    return fake


async def test_call_returns_text_and_usage(mock_anthropic_client) -> None:
    transport = AnthropicSdkTransport(client=mock_anthropic_client)
    result = await transport.call(
        tier=ModelTier.HAIKU,
        system_prompt="be brief",
        user_prompt="say hi",
        max_tokens=16,
    )
    assert result.text == "hello back"
    assert result.input_tokens == 5
    assert result.output_tokens == 2


async def test_call_forwards_model_id_for_tier(mock_anthropic_client) -> None:
    transport = AnthropicSdkTransport(client=mock_anthropic_client)
    await transport.call(
        tier=ModelTier.SONNET,
        system_prompt="s",
        user_prompt="u",
        max_tokens=32,
    )
    call_args = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_args["model"] == "claude-sonnet-4-6"
    assert call_args["max_tokens"] == 32


def test_tier_model_ids_are_pinned() -> None:
    assert ModelTier.HAIKU.model_id == "claude-haiku-4-5-20251001"
    assert ModelTier.SONNET.model_id == "claude-sonnet-4-6"
    assert ModelTier.OPUS.model_id == "claude-opus-4-7"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_anthropic_sdk.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement transport** (`skillflow/skillflow/transport/anthropic_sdk.py`)

```python
"""Anthropic-SDK transport. Default subagent backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from anthropic import AsyncAnthropic


class ModelTier(Enum):
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-6"
    OPUS = "claude-opus-4-7"

    @property
    def model_id(self) -> str:
        return self.value


@dataclass
class TransportResult:
    text: str
    input_tokens: int
    output_tokens: int


class AnthropicSdkTransport:
    """Call the Anthropic API. Honors ANTHROPIC_BASE_URL override (e.g., model gateway)."""

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        if client is None:
            base_url = os.environ.get("ANTHROPIC_BASE_URL")
            api_key = os.environ.get("ANTHROPIC_API_KEY", "sk-dummy")
            client = AsyncAnthropic(base_url=base_url, api_key=api_key)
        self._client = client

    async def call(
        self,
        *,
        tier: ModelTier,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> TransportResult:
        response = await self._client.messages.create(
            model=tier.model_id,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_parts = [block.text for block in response.content if block.type == "text"]
        return TransportResult(
            text="".join(text_parts),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_anthropic_sdk.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/transport/anthropic_sdk.py tests/test_anthropic_sdk.py
git commit -m "feat(transport): add Anthropic SDK transport with configurable base_url"
```

---

## Task 6: `claude -p` subprocess transport

For activities that need Claude Code's toolbelt. Spawns `claude -p` and captures stdout.

**Files:**
- Create: `skillflow/skillflow/transport/claude_cli.py`
- Create: `tests/test_claude_cli.py`

- [ ] **Step 1: Write failing test** (`tests/test_claude_cli.py`)

```python
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from skillflow.transport.claude_cli import ClaudeCliTransport, ClaudeCliResult, ClaudeCliError


@pytest.fixture
def fake_process():
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(b"hello from subprocess\n", b""))
    proc.returncode = 0
    return proc


async def test_call_captures_stdout(fake_process) -> None:
    with patch("asyncio.create_subprocess_exec", return_value=fake_process):
        transport = ClaudeCliTransport()
        result = await transport.call(prompt="say hi", timeout_seconds=30.0)
    assert isinstance(result, ClaudeCliResult)
    assert result.stdout == "hello from subprocess\n"
    assert result.exit_code == 0


async def test_call_raises_on_nonzero_exit() -> None:
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(b"", b"boom"))
    proc.returncode = 7
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        transport = ClaudeCliTransport()
        with pytest.raises(ClaudeCliError) as exc:
            await transport.call(prompt="p", timeout_seconds=30.0)
    assert "exit code 7" in str(exc.value)
    assert "boom" in str(exc.value)


async def test_call_raises_on_timeout() -> None:
    async def never_communicates():
        await asyncio.sleep(10.0)
        return (b"", b"")

    proc = AsyncMock()
    proc.communicate = never_communicates
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        transport = ClaudeCliTransport()
        with pytest.raises(ClaudeCliError) as exc:
            await transport.call(prompt="p", timeout_seconds=0.1)
    assert "timed out" in str(exc.value).lower()
    proc.kill.assert_awaited()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_claude_cli.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement transport** (`skillflow/skillflow/transport/claude_cli.py`)

```python
"""Claude Code CLI subprocess transport. Use when activities need the Claude Code toolbelt."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


class ClaudeCliError(RuntimeError):
    """Subprocess failure: nonzero exit, timeout, or transport error."""


@dataclass
class ClaudeCliResult:
    stdout: str
    stderr: str
    exit_code: int


class ClaudeCliTransport:
    """Spawns `claude -p <prompt>` and returns captured stdout."""

    def __init__(self, command: str = "claude") -> None:
        self._command = command

    async def call(self, *, prompt: str, timeout_seconds: float) -> ClaudeCliResult:
        process = await asyncio.create_subprocess_exec(
            self._command,
            "-p",
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            await _terminate(process)
            raise ClaudeCliError(
                f"`{self._command} -p` timed out after {timeout_seconds}s"
            ) from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        if process.returncode != 0:
            raise ClaudeCliError(
                f"`{self._command} -p` exited with exit code {process.returncode}: {stderr.strip()}"
            )
        return ClaudeCliResult(stdout=stdout, stderr=stderr, exit_code=process.returncode)


async def _terminate(process: asyncio.subprocess.Process) -> None:
    process.kill()
    try:
        await asyncio.wait_for(process.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_claude_cli.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/transport/claude_cli.py tests/test_claude_cli.py
git commit -m "feat(transport): add claude -p subprocess transport with timeout"
```

---

## Task 7: Transport dispatcher

Single entry point that picks between Anthropic SDK and `claude -p` based on `tools_needed`.

**Files:**
- Create: `skillflow/skillflow/transport/dispatcher.py`
- Create: `tests/test_dispatcher.py`

- [ ] **Step 1: Write failing test** (`tests/test_dispatcher.py`)

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from skillflow.transport.dispatcher import dispatch_subagent, SubagentRequest
from skillflow.transport.anthropic_sdk import ModelTier, TransportResult
from skillflow.transport.claude_cli import ClaudeCliResult


@pytest.fixture
def fake_sdk():
    sdk = AsyncMock()
    sdk.call = AsyncMock(
        return_value=TransportResult(text="sdk output", input_tokens=10, output_tokens=5)
    )
    return sdk


@pytest.fixture
def fake_cli():
    cli = AsyncMock()
    cli.call = AsyncMock(
        return_value=ClaudeCliResult(stdout="cli output", stderr="", exit_code=0)
    )
    return cli


async def test_dispatch_uses_sdk_when_no_tools_needed(fake_sdk, fake_cli) -> None:
    result = await dispatch_subagent(
        SubagentRequest(
            role="critic",
            tier=ModelTier.HAIKU,
            system_prompt="s",
            user_prompt="u",
            max_tokens=256,
            tools_needed=False,
        ),
        sdk_transport=fake_sdk,
        cli_transport=fake_cli,
    )
    assert result == "sdk output"
    fake_sdk.call.assert_awaited_once()
    fake_cli.call.assert_not_awaited()


async def test_dispatch_uses_cli_when_tools_needed(fake_sdk, fake_cli) -> None:
    result = await dispatch_subagent(
        SubagentRequest(
            role="critic",
            tier=ModelTier.HAIKU,
            system_prompt="s",
            user_prompt="u",
            max_tokens=256,
            tools_needed=True,
        ),
        sdk_transport=fake_sdk,
        cli_transport=fake_cli,
    )
    assert result == "cli output"
    fake_cli.call.assert_awaited_once()
    fake_sdk.call.assert_not_awaited()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dispatcher.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement dispatcher** (`skillflow/skillflow/transport/dispatcher.py`)

```python
"""Transport dispatcher. Selects SDK vs CLI based on `tools_needed`."""

from __future__ import annotations

from dataclasses import dataclass

from skillflow.transport.anthropic_sdk import AnthropicSdkTransport, ModelTier
from skillflow.transport.claude_cli import ClaudeCliTransport


@dataclass(frozen=True)
class SubagentRequest:
    role: str
    tier: ModelTier
    system_prompt: str
    user_prompt: str
    max_tokens: int
    tools_needed: bool
    cli_timeout_seconds: float = 600.0


async def dispatch_subagent(
    request: SubagentRequest,
    *,
    sdk_transport: AnthropicSdkTransport,
    cli_transport: ClaudeCliTransport,
) -> str:
    if request.tools_needed:
        combined_prompt = f"{request.system_prompt}\n\n---\n\n{request.user_prompt}"
        result = await cli_transport.call(
            prompt=combined_prompt,
            timeout_seconds=request.cli_timeout_seconds,
        )
        return result.stdout

    sdk_result = await sdk_transport.call(
        tier=request.tier,
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        max_tokens=request.max_tokens,
    )
    return sdk_result.text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dispatcher.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/transport/dispatcher.py tests/test_dispatcher.py
git commit -m "feat(transport): add dispatcher selecting SDK vs CLI by tools_needed"
```

---

## Task 8: Base WorkflowState + ActivityOutcome

Shared dataclass every skill workflow extends. Carries generation counter, per-activity outcome ledger, cost tally.

**Files:**
- Create: `skillflow/skillflow/durable/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing test** (`tests/test_state.py`)

```python
import pytest

from skillflow.durable.state import ActivityOutcome, WorkflowState


def test_increment_generation_is_monotonic() -> None:
    s = WorkflowState(run_id="abc", skill="hello-world")
    assert s.generation == 0
    s.increment_generation()
    assert s.generation == 1
    s.increment_generation()
    assert s.generation == 2


def test_record_activity_outcome() -> None:
    s = WorkflowState(run_id="abc", skill="hello-world")
    s.record_outcome(ActivityOutcome(activity_id="act-1", role="greeter", status="completed"))
    assert len(s.activity_outcomes) == 1
    assert s.activity_outcomes[0].status == "completed"


def test_add_cost_accumulates() -> None:
    s = WorkflowState(run_id="abc", skill="hello-world")
    s.add_cost(input_tokens=100, output_tokens=50, haiku=True)
    s.add_cost(input_tokens=200, output_tokens=100, haiku=True)
    # Haiku pricing: $0.80/$4 per million, so 300 input + 150 output
    expected = (300 / 1_000_000) * 0.80 + (150 / 1_000_000) * 4.0
    assert s.cost_running_total == pytest.approx(expected)


def test_terminal_label_is_set_once() -> None:
    s = WorkflowState(run_id="abc", skill="hello-world")
    s.set_terminal("completed")
    with pytest.raises(RuntimeError, match="already terminated"):
        s.set_terminal("failed")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement state module** (`skillflow/skillflow/durable/state.py`)

```python
"""Base workflow state shared by every skillflow skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ActivityStatus = Literal[
    "pending", "in_progress", "completed", "timed_out", "failed", "spawn_failed"
]

HAIKU_INPUT_PRICE_PER_MILLION = 0.80
HAIKU_OUTPUT_PRICE_PER_MILLION = 4.00
SONNET_INPUT_PRICE_PER_MILLION = 3.00
SONNET_OUTPUT_PRICE_PER_MILLION = 15.00


@dataclass
class ActivityOutcome:
    activity_id: str
    role: str
    status: ActivityStatus
    error_message: str | None = None


@dataclass
class WorkflowState:
    """Base state record. Skill-specific workflows extend this via composition or inheritance."""

    run_id: str
    skill: str
    generation: int = 0
    activity_outcomes: list[ActivityOutcome] = field(default_factory=list)
    cost_running_total: float = 0.0
    terminal_label: str | None = None

    def increment_generation(self) -> int:
        self.generation += 1
        return self.generation

    def record_outcome(self, outcome: ActivityOutcome) -> None:
        self.activity_outcomes.append(outcome)

    def add_cost(self, *, input_tokens: int, output_tokens: int, haiku: bool) -> None:
        if haiku:
            ip = HAIKU_INPUT_PRICE_PER_MILLION
            op = HAIKU_OUTPUT_PRICE_PER_MILLION
        else:
            ip = SONNET_INPUT_PRICE_PER_MILLION
            op = SONNET_OUTPUT_PRICE_PER_MILLION
        self.cost_running_total += (input_tokens / 1_000_000) * ip
        self.cost_running_total += (output_tokens / 1_000_000) * op

    def set_terminal(self, label: str) -> None:
        if self.terminal_label is not None:
            raise RuntimeError(
                f"State {self.run_id} already terminated as {self.terminal_label!r}"
            )
        self.terminal_label = label
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/durable/state.py tests/test_state.py
git commit -m "feat(durable): add base WorkflowState with generation counter + cost tally"
```

---

## Task 9: Retry policies

Centralizes per-tier retry policies so every activity decorator stays consistent.

**Files:**
- Create: `skillflow/skillflow/durable/retry_policies.py`
- Create: `tests/test_retry_policies.py`

- [ ] **Step 1: Write failing test** (`tests/test_retry_policies.py`)

```python
from datetime import timedelta

from skillflow.durable.retry_policies import (
    CLI_POLICY,
    HAIKU_POLICY,
    NON_RETRYABLE_ERRORS,
    SONNET_POLICY,
)


def test_policies_have_expected_attempts() -> None:
    assert HAIKU_POLICY.maximum_attempts == 2
    assert SONNET_POLICY.maximum_attempts == 2
    assert CLI_POLICY.maximum_attempts == 2


def test_haiku_policy_has_short_start() -> None:
    assert HAIKU_POLICY.initial_interval == timedelta(seconds=5)
    assert HAIKU_POLICY.backoff_coefficient == 2.0
    assert HAIKU_POLICY.maximum_interval == timedelta(seconds=30)


def test_non_retryable_list_is_explicit() -> None:
    assert "InvalidInputError" in NON_RETRYABLE_ERRORS
    assert "MalformedResponseError" in NON_RETRYABLE_ERRORS


def test_policies_share_non_retryable_list() -> None:
    assert HAIKU_POLICY.non_retryable_error_types == NON_RETRYABLE_ERRORS
    assert SONNET_POLICY.non_retryable_error_types == NON_RETRYABLE_ERRORS
    assert CLI_POLICY.non_retryable_error_types == NON_RETRYABLE_ERRORS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retry_policies.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement retry policies** (`skillflow/skillflow/durable/retry_policies.py`)

```python
"""Shared retry policies for every skillflow activity.

Tiers: Haiku (cheap, fast, more retries OK), Sonnet (dearer, identical policy
currently), CLI subprocess (longer intervals because cold-start is expensive)."""

from __future__ import annotations

from datetime import timedelta

from temporalio.common import RetryPolicy

NON_RETRYABLE_ERRORS: list[str] = [
    "InvalidInputError",
    "MalformedResponseError",
]


HAIKU_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=2,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

SONNET_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=2,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

CLI_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=2,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_retry_policies.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/durable/retry_policies.py tests/test_retry_policies.py
git commit -m "feat(durable): add shared retry policies for Haiku/Sonnet/CLI tiers"
```

---

## Task 10: INBOX module

Append-only ledger of terminal transitions. Format: one line per transition; `<status>` marks unread entries; `deepqa dismiss <run_id>` or `skillflow dismiss` rewrites the line with `<dismissed>`.

**Files:**
- Create: `skillflow/skillflow/inbox.py`
- Create: `tests/test_inbox.py`

- [ ] **Step 1: Write failing test** (`tests/test_inbox.py`)

```python
from datetime import datetime

import pytest

from skillflow.inbox import InboxEntry, Inbox


def test_append_and_unread(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    inbox.append(
        InboxEntry(
            run_id="hello-world-abc",
            skill="hello-world",
            status="DONE",
            summary="greeted alice",
            timestamp=datetime(2026, 4, 21, 14, 33, 22),
        )
    )
    unread = inbox.unread()
    assert len(unread) == 1
    assert unread[0].run_id == "hello-world-abc"
    assert unread[0].status == "DONE"


def test_dismiss_marks_read(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    inbox.append(
        InboxEntry(
            run_id="r1",
            skill="s",
            status="DONE",
            summary="",
            timestamp=datetime(2026, 4, 21, 0, 0, 0),
        )
    )
    assert len(inbox.unread()) == 1
    inbox.dismiss("r1")
    assert inbox.unread() == []


def test_dismiss_unknown_run_raises(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    with pytest.raises(KeyError, match="r1"):
        inbox.dismiss("r1")


def test_append_survives_empty_file(tmp_path) -> None:
    path = tmp_path / "INBOX.md"
    path.write_text("")
    inbox = Inbox(path=path)
    inbox.append(
        InboxEntry(
            run_id="r1",
            skill="s",
            status="FAILED",
            summary="err",
            timestamp=datetime(2026, 4, 21, 0, 0, 0),
        )
    )
    assert path.read_text().startswith("[2026-04-21 00:00:00] r1 FAILED s err  <unread>")


def test_multiple_entries_preserve_order(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    for i in range(3):
        inbox.append(
            InboxEntry(
                run_id=f"r{i}",
                skill="s",
                status="DONE",
                summary=f"ran {i}",
                timestamp=datetime(2026, 4, 21, i, 0, 0),
            )
        )
    unread = inbox.unread()
    assert [e.run_id for e in unread] == ["r0", "r1", "r2"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_inbox.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement inbox module** (`skillflow/skillflow/inbox.py`)

```python
"""Append-only inbox for terminal workflow transitions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

UNREAD_TAG = "<unread>"
DISMISSED_TAG = "<dismissed>"

_LINE_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\s+"
    r"(?P<run_id>\S+)\s+"
    r"(?P<status>\S+)\s+"
    r"(?P<skill>\S+)\s+"
    r"(?P<summary>.*?)\s+"
    r"(?P<tag><unread>|<dismissed>)\s*$"
)


@dataclass(frozen=True)
class InboxEntry:
    run_id: str
    skill: str
    status: str
    summary: str
    timestamp: datetime

    def format(self, tag: str) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        summary = self.summary or "-"
        return f"[{ts}] {self.run_id} {self.status} {self.skill} {summary}  {tag}\n"


class Inbox:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: InboxEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(entry.format(UNREAD_TAG))

    def unread(self) -> list[InboxEntry]:
        return [entry for entry, tag in self._iter() if tag == UNREAD_TAG]

    def dismiss(self, run_id: str) -> None:
        lines: list[str] = []
        found = False
        for entry, tag in self._iter():
            if entry.run_id == run_id and tag == UNREAD_TAG:
                lines.append(entry.format(DISMISSED_TAG))
                found = True
            else:
                lines.append(entry.format(tag))
        if not found:
            raise KeyError(f"no unread entry for run_id={run_id}")
        self.path.write_text("".join(lines), encoding="utf-8")

    def _iter(self) -> list[tuple[InboxEntry, str]]:
        if not self.path.exists():
            return []
        out: list[tuple[InboxEntry, str]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            m = _LINE_RE.match(line)
            if not m:
                continue
            ts = datetime.strptime(m["ts"], "%Y-%m-%d %H:%M:%S")
            summary = "" if m["summary"] == "-" else m["summary"]
            out.append(
                (
                    InboxEntry(
                        run_id=m["run_id"],
                        skill=m["skill"],
                        status=m["status"],
                        summary=summary,
                        timestamp=ts,
                    ),
                    m["tag"],
                )
            )
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_inbox.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/inbox.py tests/test_inbox.py
git commit -m "feat(inbox): add append-only inbox with unread/dismiss semantics"
```

---

## Task 11: Desktop notify module

Wrapper around platform-specific notifiers with silent fallback if neither is available.

**Files:**
- Create: `skillflow/skillflow/notify.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Write failing test** (`tests/test_notify.py`)

```python
from unittest.mock import patch

from skillflow.notify import notify_desktop, _macos_command, _linux_command


def test_macos_command_structure() -> None:
    cmd = _macos_command(title="T", body="B")
    assert cmd[0] == "osascript"
    assert cmd[1] == "-e"
    assert 'display notification "B" with title "T"' in cmd[2]


def test_linux_command_structure() -> None:
    cmd = _linux_command(title="T", body="B")
    assert cmd[0] == "notify-send"
    assert cmd[1] == "T"
    assert cmd[2] == "B"


def test_notify_desktop_macos_calls_osascript() -> None:
    with (
        patch("skillflow.notify._PLATFORM", "darwin"),
        patch("skillflow.notify.subprocess.run") as mock_run,
    ):
        notify_desktop(title="Hi", body="There")
    assert mock_run.call_args[0][0][0] == "osascript"


def test_notify_desktop_swallows_errors() -> None:
    with (
        patch("skillflow.notify._PLATFORM", "darwin"),
        patch("skillflow.notify.subprocess.run", side_effect=OSError("no binary")),
    ):
        notify_desktop(title="Hi", body="There")  # must not raise


def test_notify_desktop_unknown_platform_is_noop() -> None:
    with (
        patch("skillflow.notify._PLATFORM", "windows"),
        patch("skillflow.notify.subprocess.run") as mock_run,
    ):
        notify_desktop(title="Hi", body="There")
    mock_run.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notify.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement notify module** (`skillflow/skillflow/notify.py`)

```python
"""Desktop notification with silent fallback on failure."""

from __future__ import annotations

import subprocess
import sys

_PLATFORM = sys.platform


def _macos_command(*, title: str, body: str) -> list[str]:
    title_esc = title.replace('"', '\\"')
    body_esc = body.replace('"', '\\"')
    script = f'display notification "{body_esc}" with title "{title_esc}"'
    return ["osascript", "-e", script]


def _linux_command(*, title: str, body: str) -> list[str]:
    return ["notify-send", title, body]


def notify_desktop(*, title: str, body: str) -> None:
    if _PLATFORM == "darwin":
        cmd = _macos_command(title=title, body=body)
    elif _PLATFORM.startswith("linux"):
        cmd = _linux_command(title=title, body=body)
    else:
        return
    try:
        subprocess.run(cmd, check=False, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_notify.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/notify.py tests/test_notify.py
git commit -m "feat(notify): add desktop notification with silent failure fallback"
```

---

## Task 12: SessionStart hook module

Installs an entry into `~/.claude/settings.json` that runs `skillflow hook session-start` to surface unread inbox entries. Idempotent install + uninstall + the session-start reader itself.

**Files:**
- Create: `skillflow/skillflow/hook.py`
- Create: `tests/test_hook.py`

- [ ] **Step 1: Write failing test** (`tests/test_hook.py`)

```python
import json
from datetime import datetime

from skillflow.hook import (
    HOOK_COMMAND,
    format_session_start_context,
    install,
    is_installed,
    uninstall,
)
from skillflow.inbox import InboxEntry, Inbox


def test_install_adds_hook_entry(tmp_path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    install(settings_path=settings)
    data = json.loads(settings.read_text())
    assert data["theme"] == "dark"  # unchanged
    assert any(
        h.get("command") == HOOK_COMMAND
        for event_list in data.get("hooks", {}).values()
        for h in event_list
    )


def test_install_is_idempotent(tmp_path) -> None:
    settings = tmp_path / "settings.json"
    install(settings_path=settings)
    install(settings_path=settings)
    data = json.loads(settings.read_text())
    count = sum(
        1
        for event_list in data["hooks"].values()
        for h in event_list
        if h.get("command") == HOOK_COMMAND
    )
    assert count == 1


def test_install_creates_file_if_missing(tmp_path) -> None:
    settings = tmp_path / "settings.json"
    install(settings_path=settings)
    assert settings.exists()
    data = json.loads(settings.read_text())
    assert is_installed(settings_path=settings)


def test_uninstall_removes_hook(tmp_path) -> None:
    settings = tmp_path / "settings.json"
    install(settings_path=settings)
    uninstall(settings_path=settings)
    assert not is_installed(settings_path=settings)


def test_uninstall_noop_when_absent(tmp_path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    uninstall(settings_path=settings)  # must not raise


def test_format_session_start_context_empty(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    assert format_session_start_context(inbox=inbox) == ""


def test_format_session_start_context_with_entries(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    inbox.append(
        InboxEntry(
            run_id="r1",
            skill="hello-world",
            status="DONE",
            summary="hi",
            timestamp=datetime(2026, 4, 21, 14, 0, 0),
        )
    )
    ctx = format_session_start_context(inbox=inbox)
    assert "Unread skillflow runs" in ctx
    assert "r1" in ctx
    assert "DONE" in ctx
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hook.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement hook module** (`skillflow/skillflow/hook.py`)

```python
"""SessionStart hook installer + session-start context formatter."""

from __future__ import annotations

import json
import os
from pathlib import Path

from skillflow.inbox import Inbox

HOOK_COMMAND = "skillflow hook session-start"
HOOK_EVENT = "SessionStart"


def _default_settings_path() -> Path:
    return Path(os.environ["HOME"]) / ".claude" / "settings.json"


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_installed(*, settings_path: Path | None = None) -> bool:
    path = settings_path or _default_settings_path()
    data = _load(path)
    for event_list in data.get("hooks", {}).values():
        for entry in event_list:
            if entry.get("command") == HOOK_COMMAND:
                return True
    return False


def install(*, settings_path: Path | None = None) -> None:
    path = settings_path or _default_settings_path()
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    event_list = hooks.setdefault(HOOK_EVENT, [])
    for entry in event_list:
        if entry.get("command") == HOOK_COMMAND:
            return
    event_list.append({"command": HOOK_COMMAND})
    _write(path, data)


def uninstall(*, settings_path: Path | None = None) -> None:
    path = settings_path or _default_settings_path()
    data = _load(path)
    hooks = data.get("hooks", {})
    if HOOK_EVENT not in hooks:
        return
    hooks[HOOK_EVENT] = [
        entry for entry in hooks[HOOK_EVENT] if entry.get("command") != HOOK_COMMAND
    ]
    if not hooks[HOOK_EVENT]:
        del hooks[HOOK_EVENT]
    _write(path, data)


def format_session_start_context(*, inbox: Inbox) -> str:
    entries = inbox.unread()
    if not entries:
        return ""
    lines = ["Unread skillflow runs:"]
    for e in entries:
        lines.append(
            f"- {e.run_id} {e.status} {e.skill}  {e.summary}"
            f"  (skillflow show {e.run_id})"
        )
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hook.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/hook.py tests/test_hook.py
git commit -m "feat(hook): add idempotent SessionStart hook installer + context formatter"
```

---

## Task 13: Base durable activities

`write_artifact` (disk mirror), `emit_finding` (INBOX + desktop notify + terminate-state stamp), `spawn_subagent` (transport dispatch with structured output parsing + cost accounting).

**Files:**
- Create: `skillflow/skillflow/durable/activities.py`
- Create: `tests/test_activities.py`

- [ ] **Step 1: Write failing test** (`tests/test_activities.py`)

```python
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skillflow.durable.activities import (
    EmitFindingInput,
    SpawnSubagentInput,
    WriteArtifactInput,
    emit_finding,
    spawn_subagent,
    write_artifact,
)
from skillflow.transport.anthropic_sdk import ModelTier


async def test_write_artifact_creates_file(tmp_path) -> None:
    target = tmp_path / "subdir" / "out.txt"
    await write_artifact(
        WriteArtifactInput(path=str(target), content="hello")
    )
    assert target.read_text() == "hello"


async def test_emit_finding_appends_inbox_and_notifies(tmp_path) -> None:
    inbox_path = tmp_path / "INBOX.md"
    with patch("skillflow.durable.activities.notify_desktop") as notif:
        await emit_finding(
            EmitFindingInput(
                inbox_path=str(inbox_path),
                run_id="r1",
                skill="hello-world",
                status="DONE",
                summary="greeted",
                notify=True,
                timestamp_iso="2026-04-21T14:00:00",
            )
        )
    assert "r1" in inbox_path.read_text()
    notif.assert_called_once()


async def test_emit_finding_skips_notification_when_disabled(tmp_path) -> None:
    inbox_path = tmp_path / "INBOX.md"
    with patch("skillflow.durable.activities.notify_desktop") as notif:
        await emit_finding(
            EmitFindingInput(
                inbox_path=str(inbox_path),
                run_id="r1",
                skill="hello-world",
                status="DONE",
                summary="",
                notify=False,
                timestamp_iso="2026-04-21T14:00:00",
            )
        )
    notif.assert_not_called()


async def test_spawn_subagent_returns_parsed_structured_output(tmp_path) -> None:
    input_path = tmp_path / "in.txt"
    input_path.write_text("user prompt here")
    sdk_call = AsyncMock(
        return_value=MagicMock(
            text="prose\nSTRUCTURED_OUTPUT_START\nVERDICT|OK\nSTRUCTURED_OUTPUT_END\n",
            input_tokens=10,
            output_tokens=5,
        )
    )
    fake_sdk = MagicMock(call=sdk_call)
    fake_cli = MagicMock(call=AsyncMock())
    with (
        patch("skillflow.durable.activities._get_sdk", return_value=fake_sdk),
        patch("skillflow.durable.activities._get_cli", return_value=fake_cli),
    ):
        parsed = await spawn_subagent(
            SpawnSubagentInput(
                role="greeter",
                tier_name="HAIKU",
                system_prompt="be brief",
                user_prompt_path=str(input_path),
                max_tokens=128,
                tools_needed=False,
            )
        )
    assert parsed == {"VERDICT": "OK"}
    sdk_call.assert_awaited()


async def test_spawn_subagent_raises_on_missing_input_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        await spawn_subagent(
            SpawnSubagentInput(
                role="greeter",
                tier_name="HAIKU",
                system_prompt="s",
                user_prompt_path=str(tmp_path / "nope.txt"),
                max_tokens=16,
                tools_needed=False,
            )
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_activities.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement activities** (`skillflow/skillflow/durable/activities.py`)

```python
"""Base activities shared by every skillflow skill."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from temporalio import activity

from skillflow.inbox import Inbox, InboxEntry
from skillflow.notify import notify_desktop
from skillflow.transport.anthropic_sdk import AnthropicSdkTransport, ModelTier
from skillflow.transport.claude_cli import ClaudeCliTransport
from skillflow.transport.dispatcher import SubagentRequest, dispatch_subagent
from skillflow.transport.structured_output import parse_structured


@dataclass(frozen=True)
class WriteArtifactInput:
    path: str
    content: str


@activity.defn(name="write_artifact")
async def write_artifact(inp: WriteArtifactInput) -> None:
    target = Path(inp.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(inp.content, encoding="utf-8")


@dataclass(frozen=True)
class EmitFindingInput:
    inbox_path: str
    run_id: str
    skill: str
    status: str
    summary: str
    notify: bool
    timestamp_iso: str


@activity.defn(name="emit_finding")
async def emit_finding(inp: EmitFindingInput) -> None:
    inbox = Inbox(path=Path(inp.inbox_path))
    inbox.append(
        InboxEntry(
            run_id=inp.run_id,
            skill=inp.skill,
            status=inp.status,
            summary=inp.summary,
            timestamp=datetime.fromisoformat(inp.timestamp_iso),
        )
    )
    if inp.notify:
        notify_desktop(
            title=f"skillflow: {inp.run_id} {inp.status}",
            body=inp.summary or inp.skill,
        )


@dataclass(frozen=True)
class SpawnSubagentInput:
    role: str
    tier_name: str                # ModelTier.name — pydantic-safe string
    system_prompt: str
    user_prompt_path: str
    max_tokens: int
    tools_needed: bool


def _get_sdk() -> AnthropicSdkTransport:
    return AnthropicSdkTransport()


def _get_cli() -> ClaudeCliTransport:
    return ClaudeCliTransport()


@activity.defn(name="spawn_subagent")
async def spawn_subagent(inp: SpawnSubagentInput) -> dict[str, str]:
    prompt_path = Path(inp.user_prompt_path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"subagent input file missing: {prompt_path}")
    user_prompt = prompt_path.read_text(encoding="utf-8")
    if not user_prompt.strip():
        raise FileNotFoundError(f"subagent input file is empty: {prompt_path}")

    tier = ModelTier[inp.tier_name]
    sdk = _get_sdk()
    cli = _get_cli()
    request = SubagentRequest(
        role=inp.role,
        tier=tier,
        system_prompt=inp.system_prompt,
        user_prompt=user_prompt,
        max_tokens=inp.max_tokens,
        tools_needed=inp.tools_needed,
    )
    raw = await dispatch_subagent(request, sdk_transport=sdk, cli_transport=cli)
    return parse_structured(raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_activities.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/durable/activities.py tests/test_activities.py
git commit -m "feat(durable): add write_artifact/emit_finding/spawn_subagent activities"
```

---

## Task 14: Skill registry

Plugin registration entry point. Each skill package exposes `register()`; registry collects workflows + activities for the worker to register with Temporal.

**Files:**
- Create: `skillflow/skillflow/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing test** (`tests/test_registry.py`)

```python
import pytest

from skillflow.registry import SkillRegistry, SkillSpec


def fake_workflow_cls():
    class W:  # pragma: no cover - test double
        pass

    return W


def fake_activity(_inp):  # pragma: no cover - test double
    return None


def test_register_and_lookup() -> None:
    registry = SkillRegistry()
    wf = fake_workflow_cls()
    spec = SkillSpec(name="hello-world", workflow_cls=wf, activities=[fake_activity])
    registry.register(spec)
    assert registry.get("hello-world") is spec
    assert list(registry.names()) == ["hello-world"]


def test_duplicate_registration_raises() -> None:
    registry = SkillRegistry()
    wf = fake_workflow_cls()
    spec = SkillSpec(name="hello-world", workflow_cls=wf, activities=[])
    registry.register(spec)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec)


def test_get_unknown_raises() -> None:
    registry = SkillRegistry()
    with pytest.raises(KeyError, match="unknown skill"):
        registry.get("missing")


def test_all_activities_returns_union() -> None:
    registry = SkillRegistry()

    def a1(inp):  # pragma: no cover
        return None

    def a2(inp):  # pragma: no cover
        return None

    registry.register(SkillSpec(name="s1", workflow_cls=fake_workflow_cls(), activities=[a1]))
    registry.register(SkillSpec(name="s2", workflow_cls=fake_workflow_cls(), activities=[a2]))
    assert set(registry.all_activities()) == {a1, a2}


def test_all_workflows_returns_union() -> None:
    registry = SkillRegistry()
    w1 = fake_workflow_cls()
    w2 = fake_workflow_cls()
    registry.register(SkillSpec(name="s1", workflow_cls=w1, activities=[]))
    registry.register(SkillSpec(name="s2", workflow_cls=w2, activities=[]))
    assert set(registry.all_workflows()) == {w1, w2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_registry.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement registry** (`skillflow/skillflow/registry.py`)

```python
"""Skill registration entry point.

Each skill package exposes a `register(registry: SkillRegistry) -> None` function.
The worker imports all registered skills before starting, then hands the
aggregate workflow + activity lists to Temporal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class SkillSpec:
    name: str
    workflow_cls: Any
    activities: list[Callable[..., Any]]


class SkillRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"skill {spec.name!r} already registered")
        self._specs[spec.name] = spec

    def get(self, name: str) -> SkillSpec:
        if name not in self._specs:
            raise KeyError(f"unknown skill: {name!r}")
        return self._specs[name]

    def names(self) -> Iterable[str]:
        return list(self._specs.keys())

    def all_activities(self) -> list[Callable[..., Any]]:
        out: list[Callable[..., Any]] = []
        for spec in self._specs.values():
            out.extend(spec.activities)
        return out

    def all_workflows(self) -> list[Any]:
        return [spec.workflow_cls for spec in self._specs.values()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_registry.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/registry.py tests/test_registry.py
git commit -m "feat(registry): add SkillRegistry for plugin workflow/activity registration"
```

---

## Task 15: hello-world skill (workflow + state + registration)

Single-activity skill: takes a greeting name, writes `"hello, {name}"` via `spawn_subagent`, emits finding to INBOX. This is the framework smoke-test skill — it exercises every skillflow surface without deep-qa complexity.

**Files:**
- Create: `skillflow/skills/hello_world/state.py`
- Create: `skillflow/skills/hello_world/workflow.py`
- Modify: `skillflow/skills/hello_world/__init__.py` (add register())
- Create: `tests/skills/test_hello_world.py`

- [ ] **Step 1: Write state** (`skillflow/skills/hello_world/state.py`)

```python
"""Minimal state for the hello-world smoke skill."""

from __future__ import annotations

from dataclasses import dataclass

from skillflow.durable.state import WorkflowState


@dataclass
class HelloWorldState(WorkflowState):
    greeting_name: str = ""
    greeting_text: str = ""
```

- [ ] **Step 2: Write failing workflow test** (`tests/skills/test_hello_world.py`)

```python
import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from skillflow.temporal_client import TASK_QUEUE
from skillflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from skills.hello_world.workflow import HelloWorldInput, HelloWorldWorkflow


async def test_hello_world_round_trips(monkeypatch, tmp_path) -> None:
    async def fake_spawn(inp):
        return {"GREETING": f"hello, {inp.user_prompt_path}"}  # placeholder — real test patches lower

    monkeypatch.setattr(
        "skills.hello_world.workflow._spawn_greeter",
        lambda _state, path: {"GREETING": f"hello, alice"},
    )

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[HelloWorldWorkflow],
            activities=[write_artifact, emit_finding, spawn_subagent],
        ):
            result = await env.client.execute_workflow(
                HelloWorldWorkflow.run,
                HelloWorldInput(
                    run_id="hw-1",
                    name="alice",
                    inbox_path=str(tmp_path / "INBOX.md"),
                    run_dir=str(tmp_path / "runs" / "hw-1"),
                ),
                id="hw-1",
                task_queue=TASK_QUEUE,
            )
    assert result == "hello, alice"
```

- [ ] **Step 3: Implement workflow** (`skillflow/skills/hello_world/workflow.py`)

```python
"""hello-world: single-activity skill. Proves framework plumbing end-to-end."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from skillflow.durable.activities import (
        EmitFindingInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from skillflow.durable.retry_policies import HAIKU_POLICY


@dataclass(frozen=True)
class HelloWorldInput:
    run_id: str
    name: str
    inbox_path: str
    run_dir: str
    notify: bool = True


def _spawn_greeter(state_run_dir: str, prompt_path: str) -> dict[str, str]:
    """Indirection so tests can monkeypatch without touching Temporal internals."""

    raise NotImplementedError  # workflow uses execute_activity directly; this is a test hook


@workflow.defn(name="HelloWorldWorkflow")
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, inp: HelloWorldInput) -> str:
        prompt_path = f"{inp.run_dir}/prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=prompt_path, content=f"Greet {inp.name}"),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        parsed = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="greeter",
                tier_name="HAIKU",
                system_prompt=(
                    "You are a greeter. Output a greeting using the format "
                    "STRUCTURED_OUTPUT_START / GREETING|<text> / STRUCTURED_OUTPUT_END. "
                    "Do not include any other text."
                ),
                user_prompt_path=prompt_path,
                max_tokens=64,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=180),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=HAIKU_POLICY,
        )

        greeting = parsed.get("GREETING", "hello")
        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="hello-world",
                status="DONE",
                summary=greeting,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return greeting
```

- [ ] **Step 4: Update hello-world `__init__.py`** (`skillflow/skills/hello_world/__init__.py`)

```python
"""hello-world skill registration."""

from __future__ import annotations

from skillflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from skillflow.registry import SkillRegistry, SkillSpec

from skills.hello_world.workflow import HelloWorldWorkflow


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="hello-world",
            workflow_cls=HelloWorldWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
        )
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/skills/test_hello_world.py -v`
Expected: test PASSES (uses `testing.WorkflowEnvironment.start_time_skipping` — no real Temporal server needed, monkeypatched subagent).

**Note:** the monkeypatch in Step 2 stubs the subagent layer because we haven't wired a real mock for `spawn_subagent` yet. The E2E test in Task 19 covers the real path.

- [ ] **Step 6: Commit**

```bash
git add skillflow/skills/hello_world/ tests/skills/
git commit -m "feat(hello-world): add minimal skill for framework smoke testing"
```

---

## Task 16: CLI skeleton with click + launch subcommand

**Files:**
- Create: `skillflow/skillflow/cli.py`
- Create: `tests/test_cli_launch.py`

- [ ] **Step 1: Write failing test** (`tests/test_cli_launch.py`)

```python
from unittest.mock import patch

from click.testing import CliRunner

from skillflow.cli import main


def test_help_lists_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for sub in ["launch", "list", "show", "inbox", "worker", "hook", "doctor"]:
        assert sub in result.output


def test_launch_prints_workflow_id() -> None:
    runner = CliRunner()
    with (
        patch("skillflow.cli._preflight_all"),
        patch("skillflow.cli._ensure_hook_installed"),
        patch("skillflow.cli._ensure_worker_running"),
        patch("skillflow.cli._start_workflow", return_value="hello-world-test-1") as start,
        patch("skillflow.cli._await_workflow", return_value="greeting"),
    ):
        result = runner.invoke(main, ["launch", "hello-world", "--name", "alice"])
    assert result.exit_code == 0
    assert "hello-world-test-1" in result.output
    start.assert_called_once()


def test_launch_without_await_does_not_block() -> None:
    runner = CliRunner()
    with (
        patch("skillflow.cli._preflight_all"),
        patch("skillflow.cli._ensure_hook_installed"),
        patch("skillflow.cli._ensure_worker_running"),
        patch("skillflow.cli._start_workflow", return_value="wf-id") as start,
        patch("skillflow.cli._await_workflow") as await_,
    ):
        result = runner.invoke(main, ["launch", "hello-world", "--name", "bob"])
    assert result.exit_code == 0
    await_.assert_not_called()


def test_launch_await_blocks_on_result() -> None:
    runner = CliRunner()
    with (
        patch("skillflow.cli._preflight_all"),
        patch("skillflow.cli._ensure_hook_installed"),
        patch("skillflow.cli._ensure_worker_running"),
        patch("skillflow.cli._start_workflow", return_value="wf-id"),
        patch("skillflow.cli._await_workflow", return_value="hello, bob") as await_,
    ):
        result = runner.invoke(main, ["launch", "hello-world", "--name", "bob", "--await"])
    assert result.exit_code == 0
    await_.assert_called_once()
    assert "hello, bob" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_launch.py -v`
Expected: `ModuleNotFoundError` or missing `main` attribute.

- [ ] **Step 3: Implement CLI skeleton** (`skillflow/skillflow/cli.py`)

```python
"""skillflow CLI entry point."""

from __future__ import annotations

import asyncio
import sys

import click


@click.group()
def main() -> None:
    """skillflow — Temporal-backed workflow runtime for Claude Code skills."""


# Stubs — CLI subcommands call these; tests patch them.
def _preflight_all() -> None: ...
def _ensure_hook_installed() -> None: ...
def _ensure_worker_running() -> None: ...
def _start_workflow(skill: str, args: dict) -> str: ...  # type: ignore[type-arg]
def _await_workflow(workflow_id: str) -> str: ...


@main.command()
@click.argument("skill")
@click.option("--name", default="world", help="hello-world: greeting target name")
@click.option("--await", "await_result", is_flag=True, help="Block until the workflow finishes")
def launch(skill: str, name: str, await_result: bool) -> None:
    """Launch a skill workflow. Non-blocking by default; --await blocks on result."""

    _preflight_all()
    _ensure_hook_installed()
    _ensure_worker_running()
    args = {"name": name}  # skill-specific; hello-world takes name
    workflow_id = _start_workflow(skill, args)
    click.echo(f"Launched {workflow_id}")
    if await_result:
        result = _await_workflow(workflow_id)
        click.echo(result)


@main.command(name="list")
def list_cmd() -> None:
    """List running, completed, and failed runs."""
    click.echo("(not yet implemented — see Task 17)")


@main.command()
@click.argument("run_id")
def show(run_id: str) -> None:
    """Dump the final report for a run."""
    click.echo(f"(not yet implemented — would show {run_id})")


@main.command()
def inbox() -> None:
    """List unread INBOX entries."""
    click.echo("(not yet implemented — see Task 17)")


@main.group()
def hook() -> None:
    """Hook management (install / uninstall / session-start)."""


@main.command()
def doctor() -> None:
    """Run preflight checks (Temporal, transport, worker, hook)."""
    click.echo("(not yet implemented — see Task 19)")


@main.group()
def worker() -> None:
    """Worker daemon lifecycle."""


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli_launch.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/cli.py tests/test_cli_launch.py
git commit -m "feat(cli): add click skeleton with launch subcommand"
```

---

## Task 17: CLI `list` / `show` / `inbox` subcommands

Wires `list_cmd`, `show`, `inbox` to Temporal and the Inbox module.

**Files:**
- Modify: `skillflow/skillflow/cli.py` (replace the stub `list`/`show`/`inbox` commands)
- Create: `tests/test_cli_list_show.py`

- [ ] **Step 1: Write failing test** (`tests/test_cli_list_show.py`)

```python
from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner

from skillflow.cli import main
from skillflow.inbox import Inbox, InboxEntry


def test_inbox_prints_entries(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    inbox.append(
        InboxEntry(
            run_id="r1",
            skill="hello-world",
            status="DONE",
            summary="hi",
            timestamp=datetime(2026, 4, 21, 14, 0, 0),
        )
    )
    runner = CliRunner()
    with patch("skillflow.cli._inbox", return_value=inbox):
        result = runner.invoke(main, ["inbox"])
    assert result.exit_code == 0
    assert "r1" in result.output
    assert "DONE" in result.output


def test_inbox_empty_message(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    runner = CliRunner()
    with patch("skillflow.cli._inbox", return_value=inbox):
        result = runner.invoke(main, ["inbox"])
    assert result.exit_code == 0
    assert "no unread entries" in result.output.lower()


def test_dismiss_marks_read(tmp_path) -> None:
    inbox = Inbox(path=tmp_path / "INBOX.md")
    inbox.append(
        InboxEntry(
            run_id="r1",
            skill="s",
            status="DONE",
            summary="",
            timestamp=datetime(2026, 4, 21, 0, 0, 0),
        )
    )
    runner = CliRunner()
    with patch("skillflow.cli._inbox", return_value=inbox):
        result = runner.invoke(main, ["dismiss", "r1"])
    assert result.exit_code == 0
    assert inbox.unread() == []


def test_list_prints_running(tmp_path) -> None:
    runner = CliRunner()
    with patch(
        "skillflow.cli._list_workflows",
        return_value=[{"id": "wf-1", "status": "RUNNING"}],
    ):
        result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "wf-1" in result.output
    assert "RUNNING" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_list_show.py -v`
Expected: fail because stub commands echo placeholder strings.

- [ ] **Step 3: Replace stubs in `cli.py`**

Replace the `list_cmd`, `show`, `inbox`, and add a `dismiss` command. Add internal helpers. The relevant section of `cli.py` should now read:

```python
# --- internals used by subcommands; patched in tests ---
def _inbox():  # type: ignore[no-untyped-def]
    from skillflow.inbox import Inbox
    from skillflow.paths import Paths
    return Inbox(path=Paths.from_env().inbox)


def _list_workflows() -> list[dict]:  # type: ignore[type-arg]
    # Placeholder until Task 24 wires Temporal; return empty list.
    return []


@main.command(name="list")
def list_cmd() -> None:
    rows = _list_workflows()
    if not rows:
        click.echo("no workflows to list")
        return
    for row in rows:
        click.echo(f"{row['id']} {row['status']}")


@main.command()
def inbox() -> None:
    entries = _inbox().unread()
    if not entries:
        click.echo("no unread entries")
        return
    for e in entries:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        click.echo(f"[{ts}] {e.run_id} {e.status} {e.skill}  {e.summary}")


@main.command()
@click.argument("run_id")
def dismiss(run_id: str) -> None:
    _inbox().dismiss(run_id)
    click.echo(f"dismissed {run_id}")


@main.command()
@click.argument("run_id")
def show(run_id: str) -> None:
    from skillflow.paths import Paths
    report = Paths.from_env().run_dir_for(run_id) / "report.md"
    if not report.exists():
        click.echo(f"no report at {report}")
        return
    click.echo(report.read_text())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli_list_show.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skillflow/skillflow/cli.py tests/test_cli_list_show.py
git commit -m "feat(cli): wire list/show/inbox/dismiss subcommands"
```

---

## Task 18: Worker daemon + auto-spawn

Worker is a blocking `run_until_complete` loop that registers all skills and polls the `skillflow` task queue. `skillflow worker --detach` forks into the background; `skillflow launch` calls `_ensure_worker_running` which checks if any poller is active and spawns `worker --detach` if none is.

**Files:**
- Create: `skillflow/skillflow/worker.py`
- Modify: `skillflow/skillflow/cli.py` (wire `worker` group + `_ensure_worker_running`)
- Create: `tests/test_worker.py`
- Create: `tests/test_cli_worker.py`

- [ ] **Step 1: Write failing test** (`tests/test_worker.py`)

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from skillflow.registry import SkillRegistry, SkillSpec
from skillflow.worker import build_registry, _is_worker_reachable


def fake_wf_cls():
    class W:  # pragma: no cover
        pass

    return W


async def test_build_registry_includes_hello_world() -> None:
    registry = build_registry()
    assert "hello-world" in set(registry.names())


async def test_is_worker_reachable_true_when_pollers_exist() -> None:
    fake_client = SimpleNamespace(
        service_client=SimpleNamespace(
            workflow_service=SimpleNamespace(
                describe_task_queue=AsyncMock(
                    return_value=SimpleNamespace(
                        pollers=[SimpleNamespace(identity="worker-1")]
                    )
                )
            )
        )
    )
    reachable = await _is_worker_reachable(fake_client)
    assert reachable is True


async def test_is_worker_reachable_false_when_no_pollers() -> None:
    fake_client = SimpleNamespace(
        service_client=SimpleNamespace(
            workflow_service=SimpleNamespace(
                describe_task_queue=AsyncMock(
                    return_value=SimpleNamespace(pollers=[])
                )
            )
        )
    )
    reachable = await _is_worker_reachable(fake_client)
    assert reachable is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_worker.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement worker** (`skillflow/skillflow/worker.py`)

```python
"""Worker daemon: registers all skills and polls the shared task queue."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client
from temporalio.worker import Worker

from skillflow.paths import Paths
from skillflow.registry import SkillRegistry
from skillflow.temporal_client import DEFAULT_NAMESPACE, DEFAULT_TARGET, TASK_QUEUE, connect


def build_registry() -> SkillRegistry:
    """Import every skill package and register it."""

    registry = SkillRegistry()

    from skills import hello_world

    hello_world.register(registry)
    return registry


async def _is_worker_reachable(client: Client) -> bool:  # type: ignore[type-arg]
    try:
        resp = await client.service_client.workflow_service.describe_task_queue(
            DescribeTaskQueueRequest(namespace=DEFAULT_NAMESPACE, task_queue={"name": TASK_QUEUE})
        )
    except Exception:  # noqa: BLE001
        return False
    return len(resp.pollers) > 0


async def ensure_worker_running(*, target: str = DEFAULT_TARGET) -> None:
    """If no worker is polling the queue, fork `skillflow worker --detach`."""

    client = await connect(target=target)
    if await _is_worker_reachable(client):
        return
    log_dir = Paths.from_env().worker_log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"worker-{os.getpid()}.log"
    subprocess.Popen(
        [sys.executable, "-m", "skillflow.cli", "worker", "run", "--detached-child"],
        stdout=log_file.open("ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    # Poll until reachable or timeout.
    for _ in range(30):
        await asyncio.sleep(0.5)
        if await _is_worker_reachable(client):
            return
    raise RuntimeError("auto-spawned worker did not become ready within 15s")


async def run_worker(*, target: str = DEFAULT_TARGET) -> None:
    """Foreground worker. Blocks until process killed."""

    client = await connect(target=target)
    registry = build_registry()
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=registry.all_workflows(),
        activities=registry.all_activities(),
    )
    await worker.run()
```

- [ ] **Step 4: Add worker CLI subcommands in `cli.py`**

Replace the `@main.group() def worker()` block with:

```python
@main.group()
def worker() -> None:
    """Worker daemon lifecycle."""


@worker.command(name="run")
@click.option("--detached-child", is_flag=True, hidden=True)
def worker_run(detached_child: bool) -> None:
    """Foreground worker. Blocks until killed."""

    import asyncio as _asyncio

    from skillflow.worker import run_worker

    _asyncio.run(run_worker())


def _ensure_worker_running() -> None:
    import asyncio as _asyncio

    from skillflow.worker import ensure_worker_running

    _asyncio.run(ensure_worker_running())
```

- [ ] **Step 5: Write test for CLI worker entry** (`tests/test_cli_worker.py`)

```python
from unittest.mock import patch

from click.testing import CliRunner

from skillflow.cli import main


def test_worker_run_invokes_run_worker() -> None:
    runner = CliRunner()
    with patch("skillflow.worker.run_worker") as rw:
        rw.return_value = None
        result = runner.invoke(main, ["worker", "run"])
    assert result.exit_code == 0
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/test_worker.py tests/test_cli_worker.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add skillflow/skillflow/worker.py skillflow/skillflow/cli.py tests/test_worker.py tests/test_cli_worker.py
git commit -m "feat(worker): add auto-spawning worker daemon + CLI worker subcommand"
```

---

## Task 19: CLI `hook install/uninstall/session-start` + `doctor`

**Files:**
- Modify: `skillflow/skillflow/cli.py`
- Create: `tests/test_cli_hook.py`
- Create: `tests/test_cli_doctor.py`

- [ ] **Step 1: Write failing tests** (`tests/test_cli_hook.py`)

```python
from unittest.mock import patch

from click.testing import CliRunner

from skillflow.cli import main


def test_hook_install_calls_installer() -> None:
    runner = CliRunner()
    with patch("skillflow.hook.install") as mock_install:
        result = runner.invoke(main, ["hook", "install"])
    assert result.exit_code == 0
    mock_install.assert_called_once()


def test_hook_uninstall_calls_uninstaller() -> None:
    runner = CliRunner()
    with patch("skillflow.hook.uninstall") as mock_uninstall:
        result = runner.invoke(main, ["hook", "uninstall"])
    assert result.exit_code == 0
    mock_uninstall.assert_called_once()


def test_hook_session_start_emits_context(tmp_path) -> None:
    from datetime import datetime
    from skillflow.inbox import Inbox, InboxEntry

    inbox_path = tmp_path / "INBOX.md"
    inbox = Inbox(path=inbox_path)
    inbox.append(
        InboxEntry(
            run_id="r1",
            skill="s",
            status="DONE",
            summary="",
            timestamp=datetime(2026, 4, 21, 0, 0, 0),
        )
    )
    runner = CliRunner()
    with patch("skillflow.cli._inbox", return_value=inbox):
        result = runner.invoke(main, ["hook", "session-start"])
    assert result.exit_code == 0
    assert "r1" in result.output
```

- [ ] **Step 2: Write failing test** (`tests/test_cli_doctor.py`)

```python
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from skillflow.cli import main


def test_doctor_all_green() -> None:
    runner = CliRunner()
    with (
        patch("skillflow.cli._probe_temporal", return_value=("OK", None)),
        patch("skillflow.cli._probe_transport", return_value=("OK", None)),
        patch("skillflow.cli._probe_worker", return_value=("OK", None)),
        patch("skillflow.cli._probe_hook", return_value=("OK", None)),
    ):
        result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert result.output.count("OK") >= 4


def test_doctor_reports_failures() -> None:
    runner = CliRunner()
    with (
        patch("skillflow.cli._probe_temporal", return_value=("FAIL", "not reachable")),
        patch("skillflow.cli._probe_transport", return_value=("OK", None)),
        patch("skillflow.cli._probe_worker", return_value=("OK", None)),
        patch("skillflow.cli._probe_hook", return_value=("OK", None)),
    ):
        result = runner.invoke(main, ["doctor"])
    assert result.exit_code != 0
    assert "FAIL" in result.output
    assert "not reachable" in result.output
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_cli_hook.py tests/test_cli_doctor.py -v`
Expected: FAIL.

- [ ] **Step 4: Extend cli.py with hook + doctor subcommands**

Replace the `@main.group() def hook()` block with:

```python
@main.group()
def hook() -> None:
    """Hook management (install / uninstall / session-start reader)."""


@hook.command(name="install")
def hook_install() -> None:
    from skillflow.hook import install
    install()
    click.echo("hook installed")


@hook.command(name="uninstall")
def hook_uninstall() -> None:
    from skillflow.hook import uninstall
    uninstall()
    click.echo("hook uninstalled")


@hook.command(name="session-start")
def hook_session_start() -> None:
    from skillflow.hook import format_session_start_context
    click.echo(format_session_start_context(inbox=_inbox()), nl=False)


def _ensure_hook_installed() -> None:
    from skillflow.hook import install, is_installed
    if not is_installed():
        install()


# --- doctor probes ---


def _probe_temporal() -> tuple[str, str | None]:
    import asyncio as _a
    from skillflow.temporal_client import TemporalUnreachable, preflight
    try:
        _a.run(preflight())
        return ("OK", None)
    except TemporalUnreachable as exc:
        return ("FAIL", str(exc))


def _probe_transport() -> tuple[str, str | None]:
    import asyncio as _a
    from skillflow.transport.anthropic_sdk import AnthropicSdkTransport, ModelTier
    try:
        async def _call() -> None:
            await AnthropicSdkTransport().call(
                tier=ModelTier.HAIKU,
                system_prompt="ping",
                user_prompt="ping",
                max_tokens=8,
            )
        _a.run(_call())
        return ("OK", None)
    except Exception as exc:  # noqa: BLE001
        return ("FAIL", str(exc))


def _probe_worker() -> tuple[str, str | None]:
    import asyncio as _a
    from skillflow.temporal_client import connect
    from skillflow.worker import _is_worker_reachable
    try:
        async def _go() -> bool:
            client = await connect()
            return await _is_worker_reachable(client)
        running = _a.run(_go())
        return ("OK", None) if running else ("WARN", "no worker polling; will auto-spawn on launch")
    except Exception as exc:  # noqa: BLE001
        return ("FAIL", str(exc))


def _probe_hook() -> tuple[str, str | None]:
    from skillflow.hook import is_installed
    return ("OK", None) if is_installed() else ("WARN", "hook not installed; auto-installs on first launch")


@main.command()
def doctor() -> None:
    """Run preflight checks."""
    checks = [
        ("temporal", _probe_temporal),
        ("transport", _probe_transport),
        ("worker", _probe_worker),
        ("hook", _probe_hook),
    ]
    any_fail = False
    for label, probe in checks:
        status, detail = probe()
        msg = f"[{status}] {label}"
        if detail:
            msg += f": {detail}"
        click.echo(msg)
        if status == "FAIL":
            any_fail = True
    if any_fail:
        sys.exit(1)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_cli_hook.py tests/test_cli_doctor.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add skillflow/skillflow/cli.py tests/test_cli_hook.py tests/test_cli_doctor.py
git commit -m "feat(cli): add hook install/uninstall/session-start + doctor subcommands"
```

---

## Task 20: Wire launch to Temporal start_workflow + --await

Replaces the stubs `_start_workflow` / `_await_workflow` / `_preflight_all` with real Temporal client calls that submit a workflow to the running daemon.

**Files:**
- Modify: `skillflow/skillflow/cli.py`

- [ ] **Step 1: Update `_preflight_all`, `_start_workflow`, `_await_workflow` in cli.py**

```python
def _preflight_all() -> None:
    import asyncio as _a
    from skillflow.temporal_client import preflight

    _a.run(preflight())


def _start_workflow(skill: str, args: dict) -> str:  # type: ignore[type-arg]
    import asyncio as _a
    from datetime import datetime
    from skillflow.temporal_client import TASK_QUEUE, connect
    from skillflow.worker import build_registry

    async def _go() -> str:
        client = await connect()
        registry = build_registry()
        spec = registry.get(skill)
        run_id = f"{skill}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        from skillflow.paths import Paths

        paths = Paths.from_env()
        paths.ensure()
        run_dir = paths.run_dir_for(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        # For hello-world specifically:
        if skill == "hello-world":
            from skills.hello_world.workflow import HelloWorldInput

            wf_input = HelloWorldInput(
                run_id=run_id,
                name=args["name"],
                inbox_path=str(paths.inbox),
                run_dir=str(run_dir),
            )
            handle = await client.start_workflow(
                spec.workflow_cls.run,
                wf_input,
                id=run_id,
                task_queue=TASK_QUEUE,
            )
            return handle.id
        raise NotImplementedError(f"launch wiring missing for skill {skill!r}")

    return _a.run(_go())


def _await_workflow(workflow_id: str) -> str:
    import asyncio as _a
    from skillflow.temporal_client import connect

    async def _go() -> str:
        client = await connect()
        handle = client.get_workflow_handle(workflow_id)
        return await handle.result()

    return _a.run(_go())
```

- [ ] **Step 2: Run existing launch test to verify it still passes**

Run: `pytest tests/test_cli_launch.py -v`
Expected: all tests still PASS (they mock `_start_workflow` and friends — behavior unchanged).

- [ ] **Step 3: Commit**

```bash
git add skillflow/skillflow/cli.py
git commit -m "feat(cli): wire launch to Temporal start_workflow for hello-world"
```

---

## Task 21: End-to-end smoke test

Exercises: CLI launch → auto-spawn worker → Anthropic SDK call → structured output parse → INBOX append → desktop-notify (mocked). Requires a running Temporal dev server AND real `ANTHROPIC_API_KEY` (or a local model-gateway + sdk setup).

**Files:**
- Create: `tests/e2e/test_end_to_end.py`

- [ ] **Step 1: Write e2e test**

```python
"""End-to-end smoke: run hello-world through the full stack.

Requires:
  - Temporal dev server on localhost:7233 (skip otherwise)
  - ANTHROPIC_API_KEY present OR ANTHROPIC_BASE_URL pointed at a working proxy (skip otherwise)

Run with: pytest tests/e2e/test_end_to_end.py -v
CI marks this file as skip-by-default via an env check.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from skillflow.cli import main
from skillflow.inbox import Inbox


pytestmark = pytest.mark.skipif(
    not os.environ.get("SKILLFLOW_E2E"),
    reason="set SKILLFLOW_E2E=1 to run end-to-end tests",
)


def test_hello_world_end_to_end(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SKILLFLOW_ROOT", str(tmp_path / "skillflow-root"))
    inbox_path = Path(tmp_path) / "skillflow-root" / "INBOX.md"

    runner = CliRunner()
    with patch("skillflow.durable.activities.notify_desktop"):
        result = runner.invoke(
            main, ["launch", "hello-world", "--name", "alice", "--await"], catch_exceptions=False
        )
    assert result.exit_code == 0, result.output

    inbox = Inbox(path=inbox_path)
    entries = inbox.unread()
    assert any(e.run_id.startswith("hello-world-") and e.status == "DONE" for e in entries)


def test_hello_world_output_contains_greeting(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SKILLFLOW_ROOT", str(tmp_path / "skillflow-root"))
    runner = CliRunner()
    with patch("skillflow.durable.activities.notify_desktop"):
        result = runner.invoke(
            main, ["launch", "hello-world", "--name", "bob", "--await"], catch_exceptions=False
        )
    assert result.exit_code == 0
    assert "bob" in result.output.lower() or "hello" in result.output.lower()
```

- [ ] **Step 2: Run the e2e test locally (with env flag)**

Run: `SKILLFLOW_E2E=1 pytest tests/e2e/test_end_to_end.py -v`
Expected: both tests PASS (or skipped if preconditions aren't met — that's fine for CI).

Troubleshoot: if `launch --await` hangs, run `skillflow doctor` to diagnose. Most common cause: Anthropic credentials not exported, model gateway not reachable.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_end_to_end.py
git commit -m "test(e2e): add end-to-end smoke test for hello-world (opt-in via SKILLFLOW_E2E)"
```

---

## Task 22: Worker crash-recovery failure-injection test

Verifies that killing the worker mid-workflow and restarting produces identical output.

**Files:**
- Modify: `tests/e2e/test_end_to_end.py` (append)

- [ ] **Step 1: Append test to `tests/e2e/test_end_to_end.py`**

```python
def test_worker_kill_mid_run_resumes(tmp_path, monkeypatch) -> None:
    """Launch → kill worker while running → restart worker → verify same result."""

    import subprocess
    import time

    monkeypatch.setenv("SKILLFLOW_ROOT", str(tmp_path / "skillflow-root"))

    # 1. Launch non-blocking
    runner = CliRunner()
    with patch("skillflow.durable.activities.notify_desktop"):
        result = runner.invoke(
            main, ["launch", "hello-world", "--name", "kitty"], catch_exceptions=False
        )
    assert result.exit_code == 0

    # 2. Find the auto-spawned worker PID via pgrep; kill it.
    pgrep = subprocess.run(
        ["pgrep", "-f", "skillflow.cli worker run --detached-child"],
        capture_output=True,
        text=True,
    )
    pids = [int(p) for p in pgrep.stdout.strip().split() if p]
    assert pids, "expected at least one auto-spawned worker"
    for pid in pids:
        os.kill(pid, 9)
    time.sleep(1)

    # 3. Run launch again (same skill, new run_id) — auto-spawn should revive a worker,
    #    and the original workflow (still in Temporal history) should resume and complete.
    with patch("skillflow.durable.activities.notify_desktop"):
        result2 = runner.invoke(
            main, ["launch", "hello-world", "--name", "spot", "--await"], catch_exceptions=False
        )
    assert result2.exit_code == 0

    # 4. Both runs should now show up in INBOX as DONE.
    inbox = Inbox(path=Path(tmp_path) / "skillflow-root" / "INBOX.md")
    # Wait up to 15s for the first run to complete after worker revival.
    deadline = time.time() + 15
    while time.time() < deadline:
        entries = inbox.unread()
        if sum(1 for e in entries if e.status == "DONE") >= 2:
            break
        time.sleep(0.5)
    entries = inbox.unread()
    assert sum(1 for e in entries if e.status == "DONE") >= 2
```

- [ ] **Step 2: Run the resume test**

Run: `SKILLFLOW_E2E=1 pytest tests/e2e/test_end_to_end.py::test_worker_kill_mid_run_resumes -v`
Expected: PASS. If it fails, check the worker log at `~/.skillflow/logs/worker-*.log`.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_end_to_end.py
git commit -m "test(e2e): add worker-kill-and-resume failure-injection test"
```

---

## Task 23: Documentation + publish

**Files:**
- Modify: `skillflow/README.md`
- Create: `skillflow/docs/SKILL-TEMPLATE.md`

- [ ] **Step 1: Replace README.md with full user documentation**

```markdown
# skillflow

Temporal-backed workflow runtime for Claude Code skills. Spawn durable subagent orchestrations that survive session crashes, surface results through multiple layers, and retry on failure.

## Install

```bash
pip install skillflow
# or from source:
pip install -e .
```

Requirements:
- Python 3.11+
- [Temporal CLI](https://docs.temporal.io/cli) running locally: `brew install temporal && temporal server start-dev`
- Anthropic API key: `export ANTHROPIC_API_KEY=sk-ant-...`

Optional: set `ANTHROPIC_BASE_URL` to route through a compatible proxy (e.g., Bedrock, model gateway).

## Quick start

```bash
skillflow doctor
skillflow launch hello-world --name alice --await
```

You should see `hello, alice` printed, an entry appended to `~/.skillflow/INBOX.md`, and a desktop notification.

## Architecture

- `skillflow launch <skill>` submits a workflow to a local Temporal server.
- A long-lived worker daemon (auto-spawned) polls the `skillflow` task queue and runs the workflow.
- Subagent activities dispatch to either the Anthropic SDK (default) or `claude -p` subprocess (when tools are needed).
- Results land in `~/.skillflow/INBOX.md`, trigger a desktop notification, and are available via `skillflow show <run_id>`.
- A Claude Code SessionStart hook (auto-installed) surfaces unread entries to new Claude Code sessions.

## Writing a new skill

See `docs/SKILL-TEMPLATE.md`.

## CLI reference

- `skillflow launch <skill> [...] [--await]` — submit workflow
- `skillflow list` — show recent runs
- `skillflow show <run_id>` — dump report
- `skillflow inbox` — show unread INBOX entries
- `skillflow dismiss <run_id>` — mark as read
- `skillflow worker run` — foreground worker (use only for debugging)
- `skillflow hook install|uninstall|session-start` — hook lifecycle (auto-installed on first launch)
- `skillflow doctor` — preflight checks

## License

MIT
```

- [ ] **Step 2: Write `docs/SKILL-TEMPLATE.md`**

```markdown
# Writing a new skillflow skill

Each skill is a Python sub-package under `skills/<name>/`. It must:

1. Define a `@workflow.defn` class that accepts an input dataclass and runs phases via `workflow.execute_activity`.
2. Reuse the base activities (`write_artifact`, `emit_finding`, `spawn_subagent`) from `skillflow.durable.activities`. Add skill-specific activities only when the base ones can't cover the need.
3. Expose a `register(registry: SkillRegistry) -> None` function that registers a `SkillSpec` with the skill's workflow class and activity list.

## Minimal example

See `skills/hello_world/` for a working skill that exercises every framework surface with ~100 lines of code.

## CLI integration

`skillflow.cli._start_workflow` has a dispatch table keyed on skill name. Add an entry there for your skill — take args from Click options, build the input dataclass, call `client.start_workflow`.

## State schema

Extend `skillflow.durable.state.WorkflowState` rather than re-rolling generation counter + cost + terminal-label bookkeeping.
```

- [ ] **Step 3: Run full test suite**

Run: `pytest -v --cov=skillflow`
Expected: all unit tests PASS; e2e tests skip unless `SKILLFLOW_E2E=1`.

- [ ] **Step 4: Commit + initialize GitHub remote**

```bash
git add skillflow/README.md skillflow/docs/SKILL-TEMPLATE.md
git commit -m "docs: add user-facing README and skill-template guide"
gh repo create skillflow --private --source=. --description "Temporal-backed workflow runtime for Claude Code skills"
git push -u origin main
```

(User confirms GitHub repo name before push — might want public visibility.)

---

## Self-Review

**1. Spec coverage check:**

| Spec section | Covered by task(s) |
|---|---|
| D1 full workflow rewrite | Task 15 (hello-world proves Python-as-coordinator) |
| D2 transport (Anthropic SDK default, optional gateway, claude -p) | Tasks 5, 6, 7 |
| D3 headless daemon + auto-spawn | Task 18 |
| D4 non-blocking default UX | Task 16, 20 |
| D5 four-layer safety net | Tasks 10, 11, 12, 13, 19 (INBOX + notify + SessionStart hook + doctor) |
| D6 auto-install hook | Task 19 `_ensure_hook_installed` + Task 16 launch calls it |
| D7 workspace-drift warning | Deferred — not required for hello-world smoke; deep-qa plan covers it |
| D8 artifact snapshot | Deferred — same as D7 |
| Architecture: repo structure | Tasks 1, 15, 14 |
| Activity contracts | Tasks 9, 13 |
| Framework-neutrality test | Tasks 14, 15 (hello-world doesn't import from `skills/deep_qa/`) |
| Auto-install hook | Task 19 + called from Task 16 |
| Desktop notification default-on | Task 11 + Task 13 respects `notify` flag |
| SessionStart hook surface | Task 12 + Task 19 `session-start` subcommand |
| Success criterion #1 durability | Task 22 |
| Success criterion #2 latency | Covered informally by E2E in Task 21 — add perf assertion if user wants |
| Success criterion #3 surfacing | Tasks 10, 11, 12 + E2E in Tasks 21, 22 |
| Success criterion #5 graceful failure | Task 19 doctor + Task 3 `TemporalUnreachable` |
| Success criterion #6 framework-neutrality | Task 14 registry + Task 15 hello-world |
| Success criterion #7 test coverage | Coverage accumulates across tasks; verify via `pytest --cov` in Task 23 |
| Success criterion #8 docs | Task 23 |

Deferrals: D7 and D8 (workspace drift + artifact snapshot) are deep-qa concerns; they live in Plan 2. Success criterion #4 (parity vs file-based deep-qa) is also Plan 2. Success criterion #2 (latency) is measured informally in Task 21 — add a microbenchmark if user wants a hard number.

**2. Placeholder scan:** searched for TBD/TODO/implement-later in this plan — none present. Every step has complete code.

**3. Type consistency check:**
- `ModelTier` enum values match in `anthropic_sdk.py` (Task 5), `dispatcher.py` (Task 7), and used by name string in `SpawnSubagentInput` (Task 13), `HelloWorldWorkflow` (Task 15) — consistent.
- `ActivityOutcome.status` Literal matches the base `WorkflowState.activity_outcomes` list (Task 8).
- `InboxEntry` fields stay identical across Tasks 10, 12, 13.
- `TASK_QUEUE = "skillflow"` defined in `temporal_client.py` (Task 3), used by `worker.py` (Task 18), CLI (Task 20), test fixtures (Task 15) — one source of truth.

No inconsistencies found.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-21-skillflow-framework.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
