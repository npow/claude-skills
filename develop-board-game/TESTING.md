# Board Game Testing Methodology

## Overview

Every board game implementation must be testable both manually (via browser) and automatically (via Playwright). The game exposes these global APIs for automated testing:

- `window.render_game_to_text()` — returns JSON string of game state visible to local player
- `window.performMove(move)` — programmatically executes a move and returns result
- `window.startGame(config)` — bypasses lobby, starts game in a specific mode
- `window.receiveState(state)` — simulates receiving a state update (guest perspective)

## Test script usage

The Playwright test script at `scripts/test_game.js` provides a framework for testing board games. Customize it for each specific game.

### Running tests

```bash
# With npx (no global install needed)
npx @playwright/test scripts/test_game.js

# With headed browser (see what's happening)
npx @playwright/test scripts/test_game.js --headed

# With specific browser
npx @playwright/test scripts/test_game.js --project=chromium
```

### Verifying Playwright is available

```bash
# Check if playwright is available
npx playwright --version 2>/dev/null || npx @playwright/test --version 2>/dev/null

# Install if needed
npm install -D @playwright/test
npx playwright install chromium
```

## Writing game-specific tests

For each game, write tests covering these categories.

### 1. Initial state validation

```javascript
test('game initializes correctly via startGame', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));
  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));

  expect(state.phase).toBe('playing');
  expect(state.mode).toBe('local');
  expect(state.currentPlayer).toBe(0);
  expect(state.turnNumber).toBe(0);
  expect(state.players.length).toBe(2);
  expect(state.winner).toBeNull();
  expect(state.localPlayerId).toBe(0);
});
```

### 2. Legal move validation

```javascript
test('only legal moves are accepted', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  const result = await page.evaluate(() => window.performMove({ /* valid move */ }));
  expect(result.success).toBe(true);

  const bad = await page.evaluate(() => window.performMove({ invalid: true }));
  expect(bad.success).toBe(false);
  expect(bad.error).toBeDefined();
});
```

### 3. Turn progression

```javascript
test('turns alternate correctly', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  let state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.currentPlayer).toBe(0);

  await page.evaluate(() => window.performMove(/* player 0 move */));
  state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.currentPlayer).toBe(1);
});
```

### 4. Win condition detection

```javascript
test('win condition is detected', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  const moves = [ /* sequence leading to a win */ ];
  for (const move of moves) {
    await page.evaluate((m) => window.performMove(m), move);
  }

  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.phase).toBe('gameOver');
  expect(state.winner).not.toBeNull();
});
```

### 5. Score tracking

```javascript
test('scores update correctly', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  await page.evaluate(() => window.performMove(/* scoring move */));
  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.players[0].score).toBeGreaterThan(0);
});
```

### 6. UI interaction tests

```javascript
test('clicking board makes a move', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  await page.click('[data-row="0"][data-col="0"]');
  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  // Verify the move was applied
});

test('new game button returns to lobby', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));
  await page.evaluate(() => window.performMove(/* some move */));

  const btn = page.locator('#new-game-btn, [data-action="new-game"]');
  await expect(btn).toBeVisible();
  await btn.click();

  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.phase).toBe('lobby');
});
```

### 7. Multi-phase turn tests

For games with turns that have multiple phases (roll -> move -> buy):

```javascript
test('multi-phase turn progresses correctly', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  let state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.turnPhase).toBe('roll');

  // Phase 1: roll
  await page.evaluate(() => window.performMove({ type: 'roll' }));
  state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.turnPhase).toBe('move');

  // Phase 2: move
  const moveOptions = state.validMoves;
  await page.evaluate((m) => window.performMove(m), moveOptions[0]);
  state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.turnPhase).toBe('action');

  // Phase 3: end turn
  await page.evaluate(() => window.performMove({ type: 'endTurn' }));
  state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  expect(state.currentPlayer).toBe(1); // Next player
  expect(state.turnPhase).toBe('roll'); // Back to first phase
});
```

### 8. Edge case tests

- What happens when the board is full?
- What if a player has no legal moves?
- What about draw/stalemate conditions?
- Does undo work correctly (local mode only)?
- Can you start a new game mid-game?
- What happens with the maximum number of players?
- What happens with the minimum number of players?

### 9. Console error check

```javascript
test('no console errors during gameplay', async ({ page }) => {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  for (let i = 0; i < 10; i++) {
    const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
    if (state.phase === 'gameOver' || state.validMoves.length === 0) break;
    const move = state.validMoves[Math.floor(Math.random() * state.validMoves.length)];
    await page.evaluate((m) => window.performMove(m), move);
  }

  expect(errors).toEqual([]);
});
```

---

## Multiplayer-specific tests

### 10. Hidden information isolation

Verify that `getPlayerView` doesn't leak private data:

```javascript
test('player cannot see other players hidden info', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));

  // Should see own hand/private info
  // Should NOT see other player's hand — only handCount or similar
  for (const p of state.players) {
    if (p.id === state.localPlayerId) {
      // Own player: should have full private info if the game has it
      // (game-specific assertion)
    } else {
      // Other player: should NOT have 'hand' or other private fields
      expect(p.hand).toBeUndefined();
    }
  }
});
```

### 11. Valid moves only on your turn

```javascript
test('no valid moves when it is not your turn', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  // Make a move so it's player 1's turn
  const s0 = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  await page.evaluate((m) => window.performMove(m), s0.validMoves[0]);

  // Now localPlayerId is still 0, but currentPlayer is 1
  // In hot-seat mode, localPlayerId tracks currentPlayer
  // In online mode, localPlayerId is fixed — so validMoves should be empty
  // Test the online perspective:
  const state = await page.evaluate(() => {
    // Simulate being player 0 while it's player 1's turn
    const gs = window.gameState;
    const view = window.getPlayerView
      ? window.getPlayerView(gs, 0)
      : JSON.parse(window.render_game_to_text());
    return view;
  });

  if (state.currentPlayer !== 0) {
    expect(state.validMoves.length).toBe(0);
  }
});
```

### 12. Turn transition screen (hot-seat with hidden info)

```javascript
test('turn transition overlay appears between turns', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  // Make a move
  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  await page.evaluate((m) => window.performMove(m), state.validMoves[0]);

  // If game has hidden info, transition overlay should appear
  const overlay = page.locator('#turn-transition, [data-turn-transition]');
  // Only check if the game has hidden info
  const hasHiddenInfo = await page.evaluate(() =>
    window.gameState?.config?.hasHiddenInfo ?? false
  );
  if (hasHiddenInfo) {
    await expect(overlay).toBeVisible();
    // Dismiss it
    await overlay.locator('button').click();
    await expect(overlay).toBeHidden();
  }
});
```

### 13. Local split-tab communication (BroadcastChannel)

Test with two pages in the same browser context:

```javascript
test('split-tab: two tabs can play a game', async ({ browser }) => {
  const context = await browser.newContext();
  const hostPage = await context.newPage();
  const guestPage = await context.newPage();

  const gameUrl = 'file://' + path.resolve('index.html');
  await hostPage.goto(gameUrl);
  await guestPage.goto(gameUrl);

  // Host starts a game
  const roomCode = await hostPage.evaluate(() => {
    window.startGame({
      mode: 'local-split',
      players: [{ name: 'Alice' }, { name: 'Bob' }],
      isHost: true,
    });
    return window.gameState.roomCode;
  });

  // Guest joins with room code
  await guestPage.evaluate((code) => {
    window.startGame({
      mode: 'local-split',
      players: [{ name: 'Alice' }, { name: 'Bob' }],
      isHost: false,
      roomCode: code,
      localPlayerId: 1,
    });
  }, roomCode);

  // Allow BroadcastChannel to propagate
  await hostPage.waitForTimeout(200);

  // Host makes a move
  const hostState = JSON.parse(await hostPage.evaluate(() => window.render_game_to_text()));
  expect(hostState.currentPlayer).toBe(0);
  await hostPage.evaluate((m) => window.performMove(m), hostState.validMoves[0]);

  // Wait for broadcast
  await guestPage.waitForTimeout(200);

  // Guest should see updated state
  const guestState = JSON.parse(await guestPage.evaluate(() => window.render_game_to_text()));
  expect(guestState.currentPlayer).toBe(1);
  expect(guestState.turnNumber).toBe(1);

  await context.close();
});
```

### 14. Player count validation

```javascript
test('rejects invalid player count', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));

  // Try starting with too few players
  const result = await page.evaluate(() => {
    try {
      window.startGame({ mode: 'local', players: [{ name: 'Solo' }] });
      return { started: true };
    } catch (e) {
      return { started: false, error: e.message };
    }
  });

  // Game should reject or the game-specific min should be enforced
  // (Adjust assertion based on game's min player count)
});
```

### 15. AI opponent

```javascript
test('AI makes a move when it is its turn', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'ai',
    players: [{ name: 'Human' }, { name: 'Bot', isAI: true }]
  }));

  // Human makes a move
  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  await page.evaluate((m) => window.performMove(m), state.validMoves[0]);

  // Wait for AI to respond
  await page.waitForTimeout(1000);

  const after = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  // AI should have taken its turn, so it's back to human
  expect(after.currentPlayer).toBe(0);
  expect(after.turnNumber).toBeGreaterThanOrEqual(2);
});
```

### 16. Disconnection resilience (online)

This tests the logic, not actual network — we simulate disconnect via the API:

```javascript
test('game handles player disconnect gracefully', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [
      { name: 'Alice' },
      { name: 'Bob' },
      { name: 'Charlie' },
    ]
  }));

  // Simulate Bob disconnecting
  await page.evaluate(() => {
    window.gameState.players[1].connected = false;
  });

  // If it's Bob's turn, advance to next
  const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  if (state.currentPlayer === 1) {
    // Game should skip disconnected player or handle gracefully
    // (game-specific behavior)
  }

  // Game should still be playable
  expect(state.phase).toBe('playing');
});
```

---

## Lobby tests

### 17. Lobby renders on load

```javascript
test('lobby screen shown on initial load', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  const lobby = page.locator('#lobby, [data-screen="lobby"]');
  await expect(lobby).toBeVisible();

  // Board should not be visible yet
  const board = page.locator('#board, .board, [data-board]');
  await expect(board).toBeHidden();
});

test('mode selection buttons are present', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  const localBtn = page.locator('[data-mode="local"]');
  await expect(localBtn).toBeVisible();
});
```

---

## Negative tests (things that SHOULD fail)

Negative tests are as important as positive ones. They verify the rules engine rejects what it should reject.

### 18. Out-of-turn moves rejected

```javascript
test('cannot move when it is not your turn', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  // It's player 0's turn. Make a valid move.
  const s = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  await page.evaluate((m) => window.performMove(m), s.validMoves[0]);

  // Now it's player 1's turn. Try to move as player 0 again.
  // In hot-seat mode this means the validMoves are for player 1.
  // Attempt a move that was valid for player 0 but isn't for player 1.
  const s1 = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  // If player 0's old move is not in player 1's valid moves, it should be rejected
  if (!s1.validMoves.some(m => JSON.stringify(m) === JSON.stringify(s.validMoves[0]))) {
    const result = await page.evaluate((m) => window.performMove(m), s.validMoves[0]);
    expect(result.success).toBe(false);
  }
});
```

### 19. Out-of-bounds moves rejected

```javascript
test('out-of-bounds move is rejected', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  // Attempt a move to an impossible position
  const result = await page.evaluate(() =>
    window.performMove({ row: 999, col: 999 })
  );
  expect(result.success).toBe(false);
});
```

### 20. Move after game over rejected

```javascript
test('cannot move after game is over', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  // Play until game over
  for (let i = 0; i < 200; i++) {
    const state = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
    if (state.phase === 'gameOver') break;
    if (!state.validMoves || state.validMoves.length === 0) break;
    await page.evaluate((m) => window.performMove(m), state.validMoves[0]);
  }

  const finalState = JSON.parse(await page.evaluate(() => window.render_game_to_text()));
  if (finalState.phase === 'gameOver') {
    const result = await page.evaluate(() =>
      window.performMove({ type: 'anyMove' })
    );
    expect(result.success).toBe(false);
  }
});
```

### 21. Malformed move rejected

```javascript
test('malformed move objects are rejected', async ({ page }) => {
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.startGame({
    mode: 'local',
    players: [{ name: 'Alice' }, { name: 'Bob' }]
  }));

  const cases = [
    null,
    undefined,
    42,
    "not a move",
    { invalid: true },
    {},
  ];

  for (const bad of cases) {
    const result = await page.evaluate((m) => {
      try { return window.performMove(m); }
      catch (e) { return { success: false, error: e.message }; }
    }, bad);
    expect(result.success).toBe(false);
  }
});
```

---

## Visual verification checklist

After automated tests pass, visually verify. Check against [VISUAL.md](VISUAL.md) standards:

- [ ] CSS variables defined on `:root` (no hardcoded colors in component styles)
- [ ] Color palette is themed for this specific game (not generic dark mode)
- [ ] `font-family` set on `body` (not browser default serif)
- [ ] Lobby renders correctly with all mode buttons
- [ ] Player config allows name entry and count selection
- [ ] Board renders correctly at default viewport
- [ ] Board has gradients or texture (not flat single-color backgrounds)
- [ ] All pieces/tokens are visually distinct between players
- [ ] Current player indicator is visible and updates (glow animation)
- [ ] Valid moves highlighted on the local player's turn only
- [ ] Hover states on all interactive elements
- [ ] Scores update with pulse animation
- [ ] Game over state is clearly communicated (overlay with fade-in)
- [ ] New Game button returns to lobby
- [ ] Move history/game log updates correctly
- [ ] Turn transition screen works (if hidden info)
- [ ] Connection status dots show for online mode
- [ ] Turn timer displays and counts down (if enabled)
- [ ] No visual overflow or clipping
- [ ] Responsive layout works at 768px width
- [ ] Text is readable at all sizes
- [ ] Color contrast sufficient (light text on dark bg or vice versa)

## Continuous testing protocol

1. Make a change
2. Save the file
3. Run Playwright tests
4. If tests fail: diagnose using the failure table in [WORKFLOW.md](WORKFLOW.md). Do not blindly retry.
5. Open in browser and visually inspect against [VISUAL.md](VISUAL.md)
6. Check the browser console for errors
7. If anything fails: fix before writing more code
8. Update progress.md quality grades

Never accumulate multiple untested changes. One change, one test cycle.
