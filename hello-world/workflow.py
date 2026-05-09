"""hello-world: minimal skill demonstrating sagaflow's @skill decorator.

The decorator handles workflow-class generation, input dataclass synthesis,
CLI option mapping, and inbox emission. ``ctx.prompt(role, **vars)`` loads
``prompts/<role>.{system,user}.md``, substitutes ``$vars``, and returns the
parsed STRUCTURED_OUTPUT value (or dict if multi-key). See
``sagaflow.simple`` for the underlying mechanism.
"""

from __future__ import annotations

from sagaflow import skill


@skill("hello-world")
async def hello(ctx, name: str = "world") -> str:
    return await ctx.prompt("greeter", tier="SONNET", name=name)
