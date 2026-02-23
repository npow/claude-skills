---
name: ship-it
description: Takes a validated product idea and builds it into a complete, shippable project through a multi-phase pipeline with parallel subagents. Use when the user says "build this idea", "ship it", "go to product", "implement this", "make this real", or wants to turn a product spec into working code with tests, docs, and packaging. Handles TypeScript, Python, or Node.js projects end-to-end.
---

# Ship It

Transforms a product idea into a shippable project through a 6-phase pipeline. Each phase uses parallel subagents with quality gates. No phase advances until its gate passes.

## Workflow

1. **Spec** — Write a formal spec from the idea description. Output: `SPEC.md` in the project root. See [SPEC-PHASE.md](SPEC-PHASE.md).
2. **Design** — Architect the project: file structure, module boundaries, API contracts, data models. Output: `DESIGN.md`. Reviewed by a critic subagent that can reject up to 2 times. See [DESIGN-PHASE.md](DESIGN-PHASE.md).
3. **Build** — Implement all modules in parallel using subagents (one per component). Each component gets a coder subagent + reviewer subagent. Reviewer can reject up to 2 times per component. See [BUILD-PHASE.md](BUILD-PHASE.md).
4. **Test** — Write and run tests. Fix failures in a loop (max 5 iterations). Gate: all tests pass. See [TEST-PHASE.md](TEST-PHASE.md).
5. **Integrate** — Assemble components, verify imports resolve, run full build, fix any integration issues. Gate: `npm run build` or equivalent succeeds with zero errors. See [INTEGRATE-PHASE.md](INTEGRATE-PHASE.md).
6. **Package** — Generate README, LICENSE, package.json/pyproject.toml, CLI entry point, .gitignore. Initialize git repo. Gate: project runs from a clean install. See [PACKAGE-PHASE.md](PACKAGE-PHASE.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] SPEC.md exists and covers: problem, target user, core features, non-goals, success criteria
- [ ] DESIGN.md exists and covers: file tree, module boundaries, data models, API contracts
- [ ] Design was reviewed by critic subagent (not just self-approved)
- [ ] Every source file was reviewed by a reviewer subagent (not just written and shipped)
- [ ] All tests pass (`npm test` / `pytest` / equivalent exits 0)
- [ ] Build succeeds (`npm run build` / `tsc` / equivalent exits 0)
- [ ] Project runs from clean install: `rm -rf node_modules && npm install && npm run build && npm test` passes
- [ ] README has: one-liner, install instructions, usage example, configuration
- [ ] No hardcoded secrets, API keys, or credentials in source files
- [ ] No placeholder/TODO/FIXME left in shipped code (search and verify)

## Golden rules

1. **Spec before code.** Never write implementation code before SPEC.md and DESIGN.md are complete and reviewed. Design errors caught early cost 10x less than design errors caught during build.
2. **Every file gets a reviewer.** No source file ships without a reviewer subagent checking it. The reviewer is independent from the coder — never review your own code.
3. **Tests are not optional.** Every public function has at least one test. Every error path has a negative test. The test phase gate (all tests pass) is non-negotiable.
4. **Fix loops have caps.** Every fix loop (design critic, code reviewer, test fixer) has a maximum iteration count. If the cap is hit, stop and report what failed — do not loop forever.
5. **Parallel where independent, sequential where dependent.** Components without dependencies on each other build in parallel. Components with dependencies build in dependency order. Never parallelize dependent work.
6. **Clean install is the final gate.** The project must work from `rm -rf node_modules && npm install && npm run build && npm test` (or equivalent). If it doesn't, it's not shippable.
7. **Subagents get full context.** Every subagent receives the SPEC.md, DESIGN.md, and the specific files it needs. Never send a subagent to implement a module without the design doc.
8. **Fail loudly, not silently.** If a quality gate fails, report exactly what failed and why. Do not silently skip gates or mark them as passed when they didn't.

## Reference files

| File | Contents |
|------|----------|
| [SPEC-PHASE.md](SPEC-PHASE.md) | How to write the product spec from an idea |
| [DESIGN-PHASE.md](DESIGN-PHASE.md) | How to architect the project with critic review |
| [BUILD-PHASE.md](BUILD-PHASE.md) | How to parallelize component builds with reviewer subagents |
| [TEST-PHASE.md](TEST-PHASE.md) | How to write tests, run them, and fix failures in a loop |
| [INTEGRATE-PHASE.md](INTEGRATE-PHASE.md) | How to assemble components and verify the full build |
| [PACKAGE-PHASE.md](PACKAGE-PHASE.md) | How to generate docs, packaging, and verify clean install |
