# Implementation Patterns

Patterns for proxy wrappers, provider-agnostic interfaces, async/sync support, and lazy imports.

## Contents
- Proxy/wrapper pattern
- Provider-agnostic interfaces
- Async/sync dual support
- Lazy import pattern
- Dataclass patterns
- Failure diagnosis

## Proxy/wrapper pattern

Use this when the library needs to intercept calls to a third-party object (vector store, database client, HTTP client) without modifying it.

### Core proxy structure

```python
from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class Proxy:
    """Transparent proxy that intercepts specific methods and delegates everything else."""

    def __init__(self, wrapped: Any, interceptor: Any) -> None:
        # Use object.__setattr__ to avoid triggering our __setattr__ if we define one
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_interceptor", interceptor)

    def __getattr__(self, name: str) -> Any:
        """Delegate all unknown attributes to the wrapped object."""
        return getattr(self._wrapped, name)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(wrapping={type(self._wrapped).__name__})"
```

### Adding method interception

Override specific methods. Everything else falls through to `__getattr__`:

```python
class VectorStoreProxy(Proxy):
    """Intercepts read and write operations on a vector store."""

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Any]:
        """Intercept reads: validate results before returning."""
        results = self._wrapped.similarity_search(query, k=k, **kwargs)
        return self._interceptor.validate_reads(results)

    def add_documents(self, documents: list[Any], **kwargs: Any) -> list[str]:
        """Intercept writes: tag with provenance before storing."""
        tagged = self._interceptor.tag_provenance(documents)
        return self._wrapped.add_documents(tagged, **kwargs)

    def as_retriever(self, **kwargs: Any) -> Any:
        """Wrap the retriever so it also goes through validation."""
        retriever = self._wrapped.as_retriever(**kwargs)
        return RetrieverProxy(retriever, self._interceptor)
```

### Rules for proxy classes

- Always implement `__getattr__` to delegate unknown attributes
- Only override methods you need to intercept — never enumerate all methods
- Preserve method signatures (same parameters, same return types)
- The wrapped object's type is `Any` — do not import the framework type at module level
- Test that unknown attribute access works: `proxy.some_method_you_didnt_override()` must succeed

### Factory method pattern

Provide a clean entry point for creating proxies:

```python
class Shield:
    """Main entry point."""

    def __init__(self, config: ShieldConfig) -> None:
        self._config = config

    def wrap(self, store: T) -> T:
        """Wrap a vector store with validation. Returns same interface."""
        # Type: ignore needed because we're returning a proxy, not the exact type.
        # The proxy implements the same interface via delegation.
        return VectorStoreProxy(store, self)  # type: ignore[return-value]
```

The return type annotation is `T` (same as input) so callers see the original type in their IDE. The proxy satisfies this contract via `__getattr__` delegation.

## Provider-agnostic interfaces

Use this when the library needs to work with multiple backends (OpenAI, Anthropic, Ollama, vLLM) through a single interface.

### Protocol definition

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Any LLM that can generate text from a prompt."""

    def generate(self, prompt: str, *, temperature: float = 0.0) -> str:
        """Generate a completion. Returns the text content."""
        ...

    async def agenerate(self, prompt: str, *, temperature: float = 0.0) -> str:
        """Async version of generate."""
        ...
```

### Concrete implementations

Each provider lives in its own module under `adapters/`:

```python
# adapters/openai_provider.py
from __future__ import annotations

from typing import Any


class OpenAIProvider:
    """OpenAI-compatible LLM provider (works with OpenAI, vLLM, Ollama in OpenAI mode)."""

    def __init__(self, model: str = "gpt-4o", base_url: str | None = None, api_key: str | None = None) -> None:
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai is required for the OpenAI provider. "
                    "Install it with: pip install memshield[openai]"
                ) from None
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    def generate(self, prompt: str, *, temperature: float = 0.0) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
```

### Rules for provider interfaces

- Use `Protocol` (not ABC) for the interface — this enables structural typing
- Add `@runtime_checkable` so `isinstance(obj, LLMProvider)` works
- Every provider lazily imports its SDK — never at module top level
- Include `base_url` parameter on OpenAI-compatible providers — this enables local inference (Ollama, vLLM)
- Client objects are created lazily on first use, not in `__init__`

## Async/sync dual support

### Pattern: sync method wraps async, or vice versa

Pick one canonical implementation (usually async) and derive the other:

```python
import asyncio
from typing import Any


class Validator:
    """Validates memory entries. Async-first, with sync wrappers."""

    async def avalidate(self, entry: Any) -> ValidationResult:
        """Async validation — the canonical implementation."""
        # ... actual logic here ...
        return result

    def validate(self, entry: Any) -> ValidationResult:
        """Sync wrapper. Runs the async version in an event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running — safe to use asyncio.run
            return asyncio.run(self.avalidate(entry))
        else:
            # Event loop already running (e.g., inside Jupyter, async framework)
            # Create a new thread to avoid blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return loop.run_in_executor(pool, lambda: asyncio.run(self.avalidate(entry)))
```

### Rules for async/sync

- Pick one as canonical (async for I/O-heavy code, sync for CPU-heavy code)
- The non-canonical version is a thin wrapper — never duplicate logic
- Always handle the "event loop already running" case (Jupyter, async frameworks)
- Name async methods with `a` prefix: `validate` / `avalidate`, `generate` / `agenerate`
- Test both the sync and async paths

### When to use sync-first instead

If the library does no I/O in its core logic (e.g., hash computation, statistical profiling), use sync-first:

```python
class Hasher:
    """Hash chain for provenance tracking. CPU-only, sync-first."""

    def compute_hash(self, data: bytes, previous_hash: str) -> str:
        """Sync — this is pure computation, no I/O."""
        import hashlib
        combined = previous_hash.encode() + data
        return hashlib.sha256(combined).hexdigest()
```

Do not add async wrappers to sync-first code unless the caller specifically needs it.

## Lazy import pattern

For modules that depend on optional packages:

```python
# At module level: no imports of optional deps
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports are only used by type checkers, not at runtime
    import chromadb
    from langchain_core.vectorstores import VectorStore


def wrap_chroma(store: "chromadb.Collection") -> ChromaProxy:
    """Wrap a Chroma collection."""
    # Import at usage point
    try:
        import chromadb as _chromadb
    except ImportError:
        raise ImportError(
            "chromadb is required for Chroma support. "
            "Install it with: pip install packagename[chroma]"
        ) from None
    return ChromaProxy(store)
```

### Rules for lazy imports

- `from __future__ import annotations` at the top of every module (makes all annotations strings)
- `TYPE_CHECKING` guard for imports used only in type hints
- Runtime imports inside the function that uses them, with `try/except ImportError`
- Error message always includes the `pip install` command with the extras group name

## Dataclass patterns

### Use frozen dataclasses for immutable data

```python
from dataclasses import dataclass, field
from enum import Enum


class TrustLevel(Enum):
    """Trust level for a memory entry's provenance."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNTRUSTED = "untrusted"


@dataclass(frozen=True)
class ProvenanceRecord:
    """Immutable record of a memory write operation."""
    source: str
    timestamp: float
    trust_level: TrustLevel
    previous_hash: str
    entry_hash: str
    metadata: dict[str, str] = field(default_factory=dict)
```

### Rules for dataclasses

- Use `frozen=True` for data that flows through the system (records, results, configs)
- Use `Enum` for fixed sets of values (trust levels, verdict types, severity levels)
- Use `field(default_factory=...)` for mutable defaults — never `= {}` or `= []`
- Mutable state (caches, counters, accumulators) lives in regular classes, not dataclasses

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `TypeError: cannot pickle` on proxy object | Proxy doesn't implement `__reduce__` or `__getstate__` | Add `__getstate__` and `__setstate__` that delegate to wrapped object, or add `__reduce__` |
| Proxy breaks `isinstance(obj, FrameworkType)` checks | Framework code checks the type of the object | Add `__class__` property that returns the wrapped object's class, or subclass the framework type |
| `RuntimeError: This event loop is already running` | Calling `asyncio.run()` inside an already-running event loop | Use the ThreadPoolExecutor pattern from the async/sync section |
| Type checker complains about proxy return type | `wrap()` returns a proxy but annotation says `T` | Add `# type: ignore[return-value]` with a comment explaining why |
| Optional dep imported at startup despite lazy pattern | An `__init__.py` imports the adapter module at package level | Remove adapter imports from `__init__.py`. Users import adapters directly |
| If none of the above | Add `print(type(obj), dir(obj))` before the failing call to inspect what the proxy exposes. Compare against what the caller expects |
