---
name: develop-board-game
description: Creates a complete, faithful digital version of a board game as a single-file HTML/JS/CSS application. Use when the user asks to build, implement, or digitize a board game, card game, or tabletop game. Handles rules implementation, turn management, multiplayer (local hot-seat, split-tab, online P2P), UI layout, and automated testing via Playwright.
argument-hint: "[game name or description]"
---

# Develop Board Game

Build a faithful digital board game as a single HTML file. Accurate rules, multiplayer support, polished visuals.

## Workflow

1. **Research rules** — understand EVERY rule before coding. List them in a comment block at the top of the HTML file. Do not start coding until you can explain every rule. See step details in [WORKFLOW.md](WORKFLOW.md).

2. **Choose multiplayer modes** — use the decision tree in [MULTIPLAYER.md](MULTIPLAYER.md). Every game gets a lobby screen.

3. **Define game state** — single JSON-serializable source of truth. See state model in [ARCHITECTURE.md](ARCHITECTURE.md).

4. **Implement rules engine** — pure functions: `getValidMoves`, `applyMove`, `checkWinCondition`, `getNextPlayer`, `getPlayerView`. See patterns in [ARCHITECTURE.md](ARCHITECTURE.md).

5. **Build lobby UI** — mode selection, player config, online room code flow. See [WORKFLOW.md](WORKFLOW.md).

6. **Build game UI** — board, player panel, game log, status bar, controls. Follow the visual standards in [VISUAL.md](VISUAL.md). **Do not use vague aesthetics — follow the concrete CSS system.**

7. **Implement turn management** — mode-specific behavior (hot-seat transitions, host-authoritative networking, AI delay). See [MULTIPLAYER.md](MULTIPLAYER.md).

8. **Wire test APIs** — `window.render_game_to_text()`, `window.performMove(move)`, `window.startGame(config)`. See signatures in [WORKFLOW.md](WORKFLOW.md).

9. **Test** — run Playwright after EVERY meaningful change. See [TESTING.md](TESTING.md).

10. **Self-review loop** — after tests pass, review your own work against the checklist below. Fix issues. Re-test. Repeat until all checks pass. **Do not skip this step.**

11. **Track progress** — maintain `progress.md` with quality grades. See template in [WORKFLOW.md](WORKFLOW.md).

## Self-review checklist

After each major milestone, verify ALL of these. If any fail, fix before proceeding:

- [ ] Every rule from step 1 is implemented (cross-check the comment block)
- [ ] Invalid moves are rejected with clear error messages (test at least 3 illegal moves)
- [ ] Win/loss/draw conditions trigger correctly (play to completion at least once)
- [ ] `render_game_to_text()` returns enough info to verify any rule without inspecting DOM
- [ ] No console errors during a full game playthrough
- [ ] Board looks intentional, not default/generic (check against [VISUAL.md](VISUAL.md))
- [ ] Each multiplayer mode works independently
- [ ] Hidden info is never leaked (check `getPlayerView` output for opponent data)

## Golden rules

Hard mechanical rules. Never violate these.

1. **State is the only truth.** UI reads from state, never the reverse. `render(state)` is a pure function of state. No game logic reads from the DOM.
2. **Rules engine is pure.** `applyMove(state, move)` takes state + move, returns new state. No side effects. No randomness except where the game demands it (dice), and even then, the result is stored in state.
3. **Validate at boundaries.** Every move entering the system — from UI clicks, `performMove()`, or network messages — passes through `getValidMoves` before `applyMove`. No shortcuts. No "trust the caller."
4. **Never expose hidden info.** `getPlayerView(state, playerId)` is the ONLY way to derive what a player sees. The host never sends raw state to guests. `render_game_to_text()` returns the local player's view, not the full state.
5. **One change, one test.** Never accumulate untested changes. After every meaningful edit: save → test → verify. If tests fail, fix before writing more code.
6. **Diagnose, don't retry.** When a test fails, do not blindly change code and re-run. Read the error. Identify the root cause. Determine if the issue is in the rule logic, the UI wiring, or the test itself. Fix the specific problem.
7. **No magic numbers in game logic.** Board dimensions, scoring values, player limits, and turn counts must come from named constants or `config`, never inline literals scattered through code.
8. **CSS variables for all visual theming.** Colors, sizes, and spacing are defined as CSS custom properties on `:root`. Components reference variables, never hardcoded hex values. This is how you maintain visual consistency.
9. **Boring technology only.** Vanilla JS, HTML, CSS. No frameworks, no build steps, no exotic dependencies. The one exception is PeerJS from CDN for online multiplayer. If you need functionality from a library, reimplement the needed subset directly.
10. **Centralize invariants.** Extract shared logic into named functions. If the same validation or computation appears in two places, it must be one function called from both. Duplicated logic drifts.
11. **Error messages are remediation instructions.** Every validation rejection must say what was wrong AND what was expected: `"Invalid move: {row: 9, col: 0} — row must be 0-7"` not `"Invalid move"`. The agent (and the test runner) uses these messages to self-correct.

## Reference files

| File | Contents |
|------|----------|
| [WORKFLOW.md](WORKFLOW.md) | Detailed step-by-step for each workflow phase, test API signatures, progress.md template |
| [ARCHITECTURE.md](ARCHITECTURE.md) | State model, board patterns (grid/hex/card/path/territory), game mechanics, AI |
| [MULTIPLAYER.md](MULTIPLAYER.md) | Host-authoritative model, hidden info, BroadcastChannel, PeerJS, message protocol, reconnection, turn timer, simultaneous actions, mode decision tree |
| [VISUAL.md](VISUAL.md) | CSS variable system, typography, color palettes, animation standards, responsive design, data attributes |
| [TESTING.md](TESTING.md) | Playwright test patterns for all modes, negative tests, visual verification checklist |
| [scripts/test_game.js](scripts/test_game.js) | Playwright test template |
