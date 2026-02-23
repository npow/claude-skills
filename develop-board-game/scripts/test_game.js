/**
 * Board Game Playwright Test Template
 *
 * Usage:
 *   npx @playwright/test scripts/test_game.js
 *   npx @playwright/test scripts/test_game.js --headed
 *
 * This is a template. Customize the tests for the specific game being built.
 * The game must expose:
 *   - window.render_game_to_text() -> JSON string of game state
 *   - window.performMove(move) -> { success, error?, state }
 *   - window.startGame(config) -> bypasses lobby, starts in specific mode
 *   - window.receiveState(state) -> simulates state update (guest perspective)
 */

const { test, expect } = require('@playwright/test');
const path = require('path');

// Update this to point to your game's HTML file
const GAME_PATH = path.resolve(process.cwd(), 'index.html');
const GAME_URL = `file://${GAME_PATH}`;

// Default test config — adjust per game
const DEFAULT_PLAYERS = [{ name: 'Alice' }, { name: 'Bob' }];

// Helper: get parsed game state
async function getState(page) {
  const raw = await page.evaluate(() => window.render_game_to_text());
  return JSON.parse(raw);
}

// Helper: perform a move and return result
async function doMove(page, move) {
  return await page.evaluate((m) => window.performMove(m), move);
}

// Helper: start a local game bypassing the lobby
async function startLocal(page, players = DEFAULT_PLAYERS) {
  await page.evaluate((p) => window.startGame({ mode: 'local', players: p }), players);
}

// Helper: start an AI game bypassing the lobby
async function startAI(page) {
  await page.evaluate(() => window.startGame({
    mode: 'ai',
    players: [{ name: 'Human' }, { name: 'Bot', isAI: true }]
  }));
}

// Helper: collect console errors
function trackErrors(page) {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));
  return errors;
}

// ─── Lobby Tests ────────────────────────────────────────────

test.describe('Lobby', () => {
  test('lobby screen shown on initial load', async ({ page }) => {
    await page.goto(GAME_URL);
    const lobby = page.locator('#lobby, [data-screen="lobby"]');
    await expect(lobby).toBeVisible();

    const board = page.locator('#board, .board, [data-board]');
    await expect(board).toBeHidden();
  });

  test('mode selection buttons are present', async ({ page }) => {
    await page.goto(GAME_URL);
    const localBtn = page.locator('[data-mode="local"]');
    await expect(localBtn).toBeVisible();
  });

  test('startGame bypasses lobby', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const state = await getState(page);
    expect(state.phase).toBe('playing');
  });
});

// ─── Game Initialization ────────────────────────────────────

test.describe('Game Initialization', () => {
  test('page loads without errors', async ({ page }) => {
    const errors = trackErrors(page);
    await page.goto(GAME_URL);
    await page.waitForTimeout(500);
    expect(errors).toEqual([]);
  });

  test('required global APIs are available', async ({ page }) => {
    await page.goto(GAME_URL);
    const apis = await page.evaluate(() => ({
      render: typeof window.render_game_to_text === 'function',
      move: typeof window.performMove === 'function',
      start: typeof window.startGame === 'function',
    }));
    expect(apis.render).toBe(true);
    expect(apis.move).toBe(true);
    expect(apis.start).toBe(true);
  });

  test('initial state is valid', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const state = await getState(page);

    expect(state).toHaveProperty('phase', 'playing');
    expect(state).toHaveProperty('mode', 'local');
    expect(state).toHaveProperty('currentPlayer', 0);
    expect(state).toHaveProperty('localPlayerId', 0);
    expect(state).toHaveProperty('turnNumber', 0);
    expect(state).toHaveProperty('players');
    expect(state).toHaveProperty('board');
    expect(state.players.length).toBeGreaterThanOrEqual(2);
    expect(state.winner).toBeNull();
  });

  test('valid moves are available at start', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const state = await getState(page);
    expect(state.validMoves).toBeDefined();
    expect(state.validMoves.length).toBeGreaterThan(0);
  });
});

// ─── Move Execution ─────────────────────────────────────────

test.describe('Move Execution', () => {
  test('valid move succeeds and advances turn', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const state = await getState(page);

    const result = await doMove(page, state.validMoves[0]);
    expect(result.success).toBe(true);

    const newState = await getState(page);
    expect(newState.turnNumber).toBeGreaterThan(0);
  });

  test('invalid move is rejected', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);

    const result = await doMove(page, { invalid: true });
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  test('turn alternates between players', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);

    const s0 = await getState(page);
    const player0 = s0.currentPlayer;

    await doMove(page, s0.validMoves[0]);
    const s1 = await getState(page);
    expect(s1.currentPlayer).not.toBe(player0);

    await doMove(page, s1.validMoves[0]);
    const s2 = await getState(page);
    expect(s2.currentPlayer).toBe(player0);
  });
});

// ─── UI Elements ────────────────────────────────────────────

test.describe('UI Elements', () => {
  test('new game button exists and returns to lobby', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const state = await getState(page);
    await doMove(page, state.validMoves[0]);

    const btn = page.locator('#new-game-btn, [data-action="new-game"]');
    await expect(btn).toBeVisible();
    await btn.click();

    const fresh = await getState(page);
    expect(fresh.phase).toBe('lobby');
  });

  test('current player indicator is visible', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const indicator = page.locator('#current-player, [data-current-player]');
    await expect(indicator).toBeVisible();
  });

  test('game board is visible during play', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const board = page.locator('#board, .board, [data-board]');
    await expect(board).toBeVisible();
  });
});

// ─── Game Progression ───────────────────────────────────────

test.describe('Game Progression', () => {
  test('can play multiple turns without errors', async ({ page }) => {
    const errors = trackErrors(page);
    await page.goto(GAME_URL);
    await startLocal(page);

    for (let i = 0; i < 10; i++) {
      const state = await getState(page);
      if (state.phase === 'gameOver') break;
      if (!state.validMoves || state.validMoves.length === 0) break;

      const move = state.validMoves[Math.floor(Math.random() * state.validMoves.length)];
      const result = await doMove(page, move);
      expect(result.success).toBe(true);
    }

    expect(errors).toEqual([]);
  });
});

// ─── Multiplayer: Hidden Information ────────────────────────

test.describe('Hidden Information', () => {
  test('player view does not leak other players private data', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    const state = await getState(page);

    for (const p of state.players) {
      if (p.id !== state.localPlayerId) {
        // Other players should NOT have 'hand' or secret fields exposed
        expect(p.hand).toBeUndefined();
      }
    }
  });

  test('no valid moves when it is not your turn (online perspective)', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);

    const s0 = await getState(page);
    await doMove(page, s0.validMoves[0]);

    // Simulate checking from a fixed-player online perspective
    const viewAsP0 = await page.evaluate(() => {
      if (typeof window.getPlayerView === 'function') {
        return window.getPlayerView(window.gameState, 0);
      }
      return null;
    });

    if (viewAsP0 && viewAsP0.currentPlayer !== 0) {
      expect(viewAsP0.validMoves.length).toBe(0);
    }
  });
});

// ─── Multiplayer: AI Opponent ───────────────────────────────

test.describe('AI Opponent', () => {
  test('AI makes a move on its turn', async ({ page }) => {
    await page.goto(GAME_URL);
    await startAI(page);

    const state = await getState(page);
    await doMove(page, state.validMoves[0]);

    // Wait for AI
    await page.waitForTimeout(1500);

    const after = await getState(page);
    expect(after.currentPlayer).toBe(0);
    expect(after.turnNumber).toBeGreaterThanOrEqual(2);
  });
});

// ─── Multiplayer: Local Split-Tab ───────────────────────────

test.describe('Local Split-Tab (BroadcastChannel)', () => {
  test('two tabs can play a game', async ({ browser }) => {
    const context = await browser.newContext();
    const hostPage = await context.newPage();
    const guestPage = await context.newPage();

    await hostPage.goto(GAME_URL);
    await guestPage.goto(GAME_URL);

    // Check if split-tab mode is supported
    const hasSplitTab = await hostPage.evaluate(() => {
      try {
        window.startGame({
          mode: 'local-split',
          players: [{ name: 'Alice' }, { name: 'Bob' }],
          isHost: true,
        });
        return true;
      } catch {
        return false;
      }
    });

    if (!hasSplitTab) {
      test.skip();
      await context.close();
      return;
    }

    const roomCode = await hostPage.evaluate(() => window.gameState.roomCode);

    await guestPage.evaluate((code) => {
      window.startGame({
        mode: 'local-split',
        players: [{ name: 'Alice' }, { name: 'Bob' }],
        isHost: false,
        roomCode: code,
        localPlayerId: 1,
      });
    }, roomCode);

    await hostPage.waitForTimeout(200);

    // Host makes a move
    const hostState = JSON.parse(await hostPage.evaluate(() => window.render_game_to_text()));
    expect(hostState.currentPlayer).toBe(0);
    await hostPage.evaluate((m) => window.performMove(m), hostState.validMoves[0]);

    await guestPage.waitForTimeout(300);

    // Guest should see updated state
    const guestState = JSON.parse(await guestPage.evaluate(() => window.render_game_to_text()));
    expect(guestState.currentPlayer).toBe(1);
    expect(guestState.turnNumber).toBe(1);

    await context.close();
  });
});

// ─── Negative Tests ─────────────────────────────────────────

test.describe('Negative Tests', () => {
  test('malformed moves are rejected', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);

    const cases = [null, 42, 'bad', {}, { invalid: true }];
    for (const bad of cases) {
      const result = await page.evaluate((m) => {
        try { return window.performMove(m); }
        catch (e) { return { success: false, error: e.message }; }
      }, bad);
      expect(result.success).toBe(false);
    }
  });

  test('out-of-bounds move is rejected', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);

    const result = await doMove(page, { row: 999, col: 999 });
    expect(result.success).toBe(false);
  });

  test('cannot move after game over', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);

    // Play to completion
    for (let i = 0; i < 200; i++) {
      const state = await getState(page);
      if (state.phase === 'gameOver' || !state.validMoves?.length) break;
      await doMove(page, state.validMoves[0]);
    }

    const final = await getState(page);
    if (final.phase === 'gameOver') {
      const result = await doMove(page, { type: 'anyMove' });
      expect(result.success).toBe(false);
    }
  });
});

// ─── CSS Variable Verification ──────────────────────────────

test.describe('Visual Standards', () => {
  test('CSS variables are defined on :root', async ({ page }) => {
    await page.goto(GAME_URL);
    const hasVars = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      // Check for at least the core variables
      return !!(
        style.getPropertyValue('--color-bg').trim() ||
        style.getPropertyValue('--color-surface').trim() ||
        style.getPropertyValue('--color-accent').trim()
      );
    });
    expect(hasVars).toBe(true);
  });

  test('body has font-family set', async ({ page }) => {
    await page.goto(GAME_URL);
    const font = await page.evaluate(() =>
      getComputedStyle(document.body).fontFamily
    );
    // Should not be the browser default serif
    expect(font.toLowerCase()).not.toContain('times');
  });
});

// ─── Screenshots ────────────────────────────────────────────

test.describe('Screenshots', () => {
  test('capture lobby', async ({ page }) => {
    await page.goto(GAME_URL);
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'screenshot-lobby.png', fullPage: true });
  });

  test('capture initial board', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'screenshot-initial.png', fullPage: true });
  });

  test('capture mid-game', async ({ page }) => {
    await page.goto(GAME_URL);
    await startLocal(page);
    for (let i = 0; i < 5; i++) {
      const state = await getState(page);
      if (state.phase === 'gameOver' || !state.validMoves?.length) break;
      await doMove(page, state.validMoves[0]);
    }
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'screenshot-midgame.png', fullPage: true });
  });
});
