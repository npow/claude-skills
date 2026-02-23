# Workflow Details

Detailed guidance for each step in the core workflow.

## Step 1: Research rules

Before writing any code, fully understand the game:

- Identify ALL rules: setup, turn structure, legal moves, scoring, win/loss conditions, edge cases
- Note player count (min, max), components (board, cards, dice, tokens), and any variants
- Determine if the game has **hidden information** (card hands, face-down tiles, secret roles)
- Determine if the game has **simultaneous actions** (secret bidding, card selection)
- Determine **turn structure**: simple alternating, multi-phase turns, or simultaneous
- If the user provides a rulebook or reference, read it completely

Write a comment block at the top of `index.html` listing every rule:

```html
<!--
  GAME RULES: [Game Name]
  Players: 2-4
  Turn structure: alternating

  Setup:
  - Rule 1
  - Rule 2

  Turn actions:
  - Rule 3
  - Rule 4

  Scoring:
  - Rule 5

  Win condition:
  - Rule 6

  Edge cases:
  - Rule 7
-->
```

**Do not start coding until you can explain every rule.**

## Step 5: Build the lobby UI

The game opens to a lobby screen, not the board:

- **Mode buttons**: Local Game, Host Online, Join Online, vs AI
- **Player config**: player count selector (within game's min/max), name inputs
- **Online host view**: generated room code, list of connected players, Start button (enabled when enough players join)
- **Online join view**: room code input, Join button, connection status
- **Player count** must respect the game's rules (e.g., Chess is always 2, Catan is 3-4)

```html
<div id="lobby" data-screen="lobby">
  <h1>[Game Name]</h1>
  <div class="mode-buttons">
    <button data-mode="local">Local Game</button>
    <button data-mode="online-host">Host Online Game</button>
    <button data-mode="online-join">Join Online Game</button>
    <button data-mode="ai">Play vs AI</button>
  </div>
  <!-- Additional config panels shown per mode -->
</div>
```

When all players are ready, transition `gameState.phase` from `"lobby"` to `"playing"` and render the board.

## Step 8: Test API signatures

Every game must expose these globals:

### `window.render_game_to_text()`

Returns a JSON string of game state visible to the local player:

```javascript
window.render_game_to_text = function() {
  return JSON.stringify({
    phase: gameState.phase,
    mode: gameState.mode,
    currentPlayer: gameState.currentPlayer,
    localPlayerId: gameState.localPlayerId,
    turnNumber: gameState.turnNumber,
    turnPhase: gameState.turnPhase,
    winner: gameState.winner,
    roomCode: gameState.roomCode,
    players: gameState.players.map(p => ({
      id: p.id,
      name: p.name,
      score: p.score,
      connected: p.connected,
      isAI: p.isAI,
      isLocal: p.isLocal,
    })),
    board: getVisibleBoard(gameState, gameState.localPlayerId),
    validMoves: gameState.currentPlayer === gameState.localPlayerId
      ? gameState.validMoves : [],
    lastMove: gameState.history[gameState.history.length - 1]?.move ?? null,
    turnTimer: gameState.turnTimer,
  });
};
```

Must include enough detail for tests to verify any game rule without inspecting the DOM.

### `window.performMove(move)`

Programmatically make a move. Routes through the same validation as UI clicks:

```javascript
window.performMove = function(move) {
  // Validate via getValidMoves, apply via applyMove, render
  // Returns { success: boolean, error?: string, state: playerView }
};
```

### `window.startGame(config)`

Bypass the lobby for automated testing:

```javascript
window.startGame = function(config) {
  // config: { mode: 'local'|'ai'|'local-split', players: [{ name, isAI? }], ... }
  // Sets up game state and renders the board directly
};
```

### `window.getPlayerView(state, playerId)` (optional but recommended)

Expose the player view function for hidden-info testing:

```javascript
window.getPlayerView = function(state, playerId) {
  // Returns filtered state for the given player
};
```

## Step 10: Self-review loop

This is the critical feedback loop. After automated tests pass:

1. **Rules audit**: Go through the comment block from step 1 line by line. For each rule, verify it works by calling `performMove` with the relevant move and checking the result.

2. **Negative testing**: Try at least 3 moves that SHOULD be illegal and verify they're rejected. Try making a move when it's not your turn. Try moves outside the board boundaries. Try moves that violate game-specific rules.

3. **Visual review**: Open the game in a browser (or take a screenshot). Check against [VISUAL.md](VISUAL.md). Is the board clearly themed for this game? Are CSS variables defined on `:root`? Is the layout responsive?

4. **Hidden info check** (if applicable): Call `getPlayerView(state, 0)` and verify player 1's hand/private data is NOT present. Call `getPlayerView(state, 1)` and verify player 0's data is NOT present.

5. **Full game playthrough**: Play a complete game from start to game-over using `performMove`. Verify the winner is correctly identified.

If any check fails: fix the issue, re-run tests, re-check. Do not proceed until all checks pass.

### Failure diagnosis protocol

When something goes wrong, follow this triage:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Test assertion fails on game state | Rule logic bug in `applyMove` or `getValidMoves` | Add a minimal reproduction: set up state, apply specific move, check specific field |
| UI doesn't reflect state | `render()` not reading from state correctly | Check that render reads `gameState` not a stale reference; add a `console.log(JSON.stringify(gameState))` to confirm |
| Move accepted when it shouldn't be | `getValidMoves` returns too many moves | Log the valid moves list and the incoming move; find why the illegal move matches |
| Move rejected when it should work | `movesEqual` comparison failing | Log both the move object and the valid moves; check for missing/extra fields |
| Online mode: guest doesn't see update | Broadcast not firing or message lost | Log messages on both host and guest; check that `broadcastState` runs after `applyMove` |
| Hidden info leaked | `getPlayerView` not filtering properly | Call it directly with a test playerId and inspect the output |

**The fix is almost never "try a different approach." The fix is understanding why the current approach failed.**

## Step 11: progress.md template

```markdown
# [Game Name] - Digital Implementation

## Original prompt
[Paste the user's original request]

## Rules implemented
| # | Rule | Status | Verified |
|---|------|--------|----------|
| 1 | [Rule description] | done | yes/no |
| 2 | [Rule description] | done | yes/no |

## Play modes
| Mode | Status | Tested |
|------|--------|--------|
| Local hot-seat | done/wip/skip | yes/no |
| Local split-tab | done/wip/skip | yes/no |
| Online P2P | done/wip/skip | yes/no |
| vs AI | done/wip/skip | yes/no |

## Quality grades
| Area | Grade | Notes |
|------|-------|-------|
| Rules fidelity | A/B/C | All rules implemented and verified? |
| Visual polish | A/B/C | Follows VISUAL.md? Themed? Not generic? |
| Multiplayer | A/B/C | All modes working? Hidden info safe? |
| Edge cases | A/B/C | Boundary conditions tested? |
| Test coverage | A/B/C | All test categories passing? |

Grading: A = verified and solid, B = works but has known gaps, C = incomplete

## Known issues
(none yet)

## Iteration log
- [date/step] What changed, what was tested, what was found
```

Update after each meaningful chunk of work. The quality grades help identify where to focus next.
