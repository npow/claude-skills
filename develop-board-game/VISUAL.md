# Visual Design Standards

Concrete, mechanical rules for visual quality. Follow these instead of improvising aesthetics.

## CSS variable system (mandatory)

Every game must define a complete variable set on `:root`. Components reference variables, never hardcoded values. This is golden rule #8.

```css
:root {
  /* --- Color palette --- */
  --color-bg: #1a1a2e;           /* Page background */
  --color-surface: #16213e;       /* Board, panels */
  --color-surface-alt: #1c2a4a;   /* Alternating cells, secondary panels */
  --color-border: #2d3a5c;        /* Subtle borders */
  --color-text: #e8e8e8;          /* Primary text */
  --color-text-muted: #8892a4;    /* Secondary text, labels */
  --color-accent: #e94560;        /* Highlights, active player, selected piece */
  --color-accent-hover: #ff6b81;  /* Hover state of accent */
  --color-success: #4ecdc4;       /* Valid moves, positive feedback */
  --color-warning: #ffe66d;       /* Alerts, timers low */
  --color-error: #ff6b6b;         /* Invalid moves, errors */

  /* --- Player colors (expand as needed) --- */
  --color-player-0: #4ecdc4;
  --color-player-1: #e94560;
  --color-player-2: #ffe66d;
  --color-player-3: #a06cd5;

  /* --- Typography --- */
  --font-main: system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-md: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
  --font-size-2xl: 2rem;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-bold: 700;

  /* --- Spacing --- */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* --- Board --- */
  --cell-size: 60px;
  --board-gap: 1px;
  --board-radius: 8px;
  --piece-size: calc(var(--cell-size) * 0.7);

  /* --- Transitions --- */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 400ms ease;

  /* --- Shadows --- */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
}
```

### Theme selection

Choose a palette that matches the game. Override the base variables:

```css
/* Classic wood/parchment — Chess, Go, Backgammon */
:root {
  --color-bg: #2c1810;
  --color-surface: #f0d9b5;
  --color-surface-alt: #b58863;
  --color-accent: #7b2d26;
  --color-text: #2c1810;
  --color-text-muted: #6b4423;
}

/* Card table felt — Poker, Blackjack, Uno */
:root {
  --color-bg: #0a3d1a;
  --color-surface: #1a7a3a;
  --color-surface-alt: #15632f;
  --color-accent: #c41e3a;
  --color-text: #f0f0f0;
}

/* Nature/terrain — Catan, Risk */
:root {
  --color-bg: #2d4a22;
  --color-surface: #8fbc8f;
  --color-surface-alt: #6b9e6b;
  --color-accent: #daa520;
  --color-text: #f5f5dc;
}
```

**Always customize the palette for the specific game.** A generic dark theme is AI slop.

## Typography rules

```css
body {
  font-family: var(--font-main);
  font-size: var(--font-size-md);
  color: var(--color-text);
  line-height: 1.5;
}

h1, h2, .game-title { font-weight: var(--font-weight-bold); }
.label, .score-label { font-size: var(--font-size-sm); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.score-value { font-family: var(--font-mono); font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); }
```

**Do not use the browser default serif font.** Always set `font-family` on `body`.

## Layout structure

```css
body {
  margin: 0;
  min-height: 100vh;
  background: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.game-container {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-lg);
  max-width: 1200px;
  width: 100%;
}

.board-area {
  flex: 0 0 auto;
}

.sidebar {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

/* Responsive: stack on narrow screens */
@media (max-width: 768px) {
  .game-container { flex-direction: column; align-items: center; }
  .sidebar { width: 100%; flex-direction: row; overflow-x: auto; }
  :root { --cell-size: min(50px, calc((100vw - 40px) / var(--cols, 8))); }
}
```

## Board rendering

### Grid boards

```css
.board {
  display: grid;
  grid-template-columns: repeat(var(--cols, 8), var(--cell-size));
  grid-template-rows: repeat(var(--rows, 8), var(--cell-size));
  gap: var(--board-gap);
  border-radius: var(--board-radius);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  /* Subtle texture: use a gradient, not flat color */
  background: linear-gradient(135deg, var(--color-border) 0%, rgba(0,0,0,0.1) 100%);
}

.cell {
  width: var(--cell-size);
  height: var(--cell-size);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: calc(var(--cell-size) * 0.6);
  transition: background var(--transition-fast);
  cursor: default;
  position: relative;
}

.cell.interactive {
  cursor: pointer;
}

.cell.interactive:hover {
  filter: brightness(1.15);
}

.cell.valid-move::after {
  content: '';
  width: 30%;
  height: 30%;
  background: var(--color-success);
  opacity: 0.5;
  border-radius: 50%;
  position: absolute;
}

.cell.last-move {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}
```

### Card rendering

```css
.card {
  width: 70px;
  height: 100px;
  border-radius: 8px;
  background: white;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-lg);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  cursor: pointer;
  user-select: none;
}

.card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-md);
}

.card.selected {
  outline: 3px solid var(--color-accent);
  transform: translateY(-8px);
}

.card.face-down {
  background: linear-gradient(135deg, var(--color-surface) 25%, var(--color-surface-alt) 75%);
  background-size: 10px 10px;
}
```

## Interactive element standards

```css
/* Buttons */
button {
  font-family: var(--font-main);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  padding: var(--space-sm) var(--space-md);
  border: none;
  border-radius: 6px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast);
}

button:hover {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
}

button:active {
  transform: translateY(0);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Input fields */
input, select {
  font-family: var(--font-main);
  font-size: var(--font-size-md);
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
}
```

## Animation standards

Use transitions for state changes, keyframe animations for attention:

```css
/* Piece placement — smooth position transitions */
.piece {
  transition: top var(--transition-normal), left var(--transition-normal);
}

/* Score update — brief pulse */
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}
.score-updated { animation: pulse 300ms ease; }

/* Turn indicator — gentle glow */
@keyframes glow {
  0%, 100% { box-shadow: 0 0 8px var(--color-accent); }
  50% { box-shadow: 0 0 16px var(--color-accent); }
}
.active-player { animation: glow 2s infinite; }

/* Dice roll — shake */
@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-10deg); }
  75% { transform: rotate(10deg); }
}
.rolling { animation: shake 150ms ease 3; }

/* Game over overlay — fade in */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.game-over-overlay { animation: fadeIn var(--transition-slow); }
```

**Use animations purposefully:** piece movement, score changes, turn transitions, game over. Do not animate everything.

## Player info panel

```css
.player-panel {
  background: var(--color-surface);
  border-radius: var(--board-radius);
  padding: var(--space-md);
  box-shadow: var(--shadow-sm);
}

.player-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  border-radius: 6px;
  transition: background var(--transition-fast);
}

.player-row.active {
  background: rgba(255, 255, 255, 0.05);
}

.player-color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.connection-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}
.connection-status.disconnected {
  background: var(--color-error);
}
```

## Turn transition overlay (hidden info games)

```css
.turn-transition {
  position: fixed;
  inset: 0;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fadeIn var(--transition-normal);
}

.turn-transition h2 {
  font-size: var(--font-size-2xl);
  margin-bottom: var(--space-lg);
}
```

## Data attributes for testing

Always add `data-*` attributes for Playwright:

```html
<div class="cell" data-row="0" data-col="3" data-piece="knight" data-player="0"></div>
<button id="new-game-btn" data-action="new-game">New Game</button>
<div id="current-player" data-current-player data-player="0">Player 1's turn</div>
<div id="score-0" data-score="5">5</div>
<div id="lobby" data-screen="lobby"></div>
<div id="board" data-board></div>
<div id="turn-transition" data-turn-transition hidden></div>
```

## Anti-patterns (avoid these)

- **Flat, unstyled backgrounds.** Always use gradients, subtle textures, or themed colors.
- **Browser default fonts.** Always set `font-family` on `body`.
- **Hardcoded colors.** Every color comes from a CSS variable.
- **No hover/focus states.** Every interactive element needs visual feedback.
- **Giant emoji as game pieces.** Use sized Unicode symbols, SVG, or CSS shapes. Style them with the player's color variable.
- **Walls of text in the UI.** Keep labels short. Use icons or symbols where possible.
- **Inconsistent spacing.** Use the spacing variables. If padding looks "roughly right," it's probably wrong — use the exact variable.
