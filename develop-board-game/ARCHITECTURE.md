# Board Game Architecture Patterns

## Single-file structure

All board games follow this HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Game Name]</title>
  <style>
    /* All CSS here */
  </style>
</head>
<body>
  <!-- Game UI here -->
  <script>
    /* All JS here */
  </script>
</body>
</html>
```

## State management pattern

Every game uses a centralized immutable state pattern, with multiplayer awareness:

```javascript
// Deep clone utility
function cloneState(state) {
  return JSON.parse(JSON.stringify(state));
}

// State transitions are pure functions
function applyMove(state, move) {
  const next = cloneState(state);
  // Modify next based on move
  return next;
}

// Player-specific view: filters state to hide other players' private info
function getPlayerView(state, playerId) {
  return {
    phase: state.phase,
    mode: state.mode,
    currentPlayer: state.currentPlayer,
    localPlayerId: playerId,
    turnNumber: state.turnNumber,
    turnPhase: state.turnPhase,
    winner: state.winner,
    roomCode: state.roomCode,
    board: getVisibleBoard(state, playerId),
    players: state.players.map((p, i) => ({
      id: p.id,
      name: p.name,
      score: p.score,
      connected: p.connected,
      isAI: p.isAI,
      isLocal: i === playerId,
      // Include private info only for the requesting player
      ...(i === playerId ? { hand: p.hand } : { handCount: p.hand?.length ?? 0 }),
    })),
    validMoves: state.currentPlayer === playerId ? getValidMoves(state) : [],
    lastMove: state.history[state.history.length - 1]?.move ?? null,
    turnTimer: state.turnTimer,
  };
}

// Single render function driven by state
function render(state) {
  // In multiplayer, always render from local player's perspective
  const view = getPlayerView(state, state.localPlayerId ?? state.currentPlayer);
  // Update all DOM elements from view
  // Never read DOM to determine game logic
}

// Global state reference
let gameState = createInitialState();

function makeMove(move) {
  const validMoves = getValidMoves(gameState);
  if (!validMoves.some(m => movesEqual(m, move))) {
    return { success: false, error: 'Invalid move' };
  }

  gameState.history.push({ move, player: gameState.currentPlayer });
  gameState = applyMove(gameState, move);
  gameState.validMoves = getValidMoves(gameState);

  // Check win condition
  const winner = checkWinCondition(gameState);
  if (winner !== null) {
    gameState.phase = 'gameOver';
    gameState.winner = winner;
  }

  render(gameState);

  // If online/split-tab host, broadcast player-specific views
  if (gameState.isHost && network) {
    network.broadcastState(gameState, getPlayerView);
  }

  // If next player is AI, trigger AI move after delay
  if (gameState.phase === 'playing' && gameState.players[gameState.currentPlayer]?.isAI) {
    setTimeout(() => {
      const aiChoice = aiMove(gameState);
      makeMove(aiChoice);
    }, 400);
  }

  return { success: true, state: getPlayerView(gameState, gameState.localPlayerId) };
}
```

## Board type patterns

### Grid-based boards (Chess, Checkers, Go, Othello)

```javascript
// Board as 2D array
const board = Array.from({ length: rows }, () => Array(cols).fill(null));

// CSS Grid layout
.board {
  display: grid;
  grid-template-columns: repeat(var(--cols), var(--cell-size));
  grid-template-rows: repeat(var(--rows), var(--cell-size));
  gap: 1px;
}

// Cell addressing
.cell[data-row][data-col] { }

// Alternating colors for checker patterns
.cell:nth-child(odd) { }
```

### Hex-based boards (Settlers of Catan, Hive)

```javascript
// Hex grid with axial coordinates (q, r)
const hexBoard = new Map(); // key: "q,r" -> value: hex data

// CSS hex layout using offset positioning
.hex {
  width: var(--hex-size);
  height: calc(var(--hex-size) * 1.1547);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
}

// Hex positioning formula
function hexToPixel(q, r) {
  const x = hexSize * (3/2 * q);
  const y = hexSize * (Math.sqrt(3)/2 * q + Math.sqrt(3) * r);
  return { x, y };
}
```

### Card-based games (Poker, Uno, Solitaire)

```javascript
// Card representation
const card = { suit: 'hearts', rank: 'A', faceUp: true };

// Deck operations
function shuffle(deck) {
  const d = [...deck];
  for (let i = d.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [d[i], d[j]] = [d[j], d[i]];
  }
  return d;
}

// Card CSS
.card {
  width: 70px;
  height: 100px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2em;
  transition: transform 0.2s;
}
.card:hover { transform: translateY(-8px); }
```

### Path/track boards (Monopoly, Snakes & Ladders)

```javascript
// Linear track with special positions
const track = Array.from({ length: totalSpaces }, (_, i) => ({
  id: i,
  type: 'normal', // or 'property', 'chance', 'tax', etc.
  position: calculatePosition(i), // x, y for rendering
}));

// Player positions on track
players.forEach(p => {
  const space = track[p.position];
  // Render token at space.position
});
```

### Territory/area boards (Risk, Diplomacy)

```javascript
// SVG-based territories
// Define regions as SVG paths, handle click on path elements
<svg viewBox="0 0 1000 600">
  <path id="territory-1" d="M..." class="territory" data-owner="0" />
  <path id="territory-2" d="M..." class="territory" data-owner="1" />
</svg>

// Adjacency graph
const adjacency = {
  'territory-1': ['territory-2', 'territory-3'],
  'territory-2': ['territory-1', 'territory-4'],
};
```

## Common game mechanics

### Dice rolling

```javascript
function rollDice(count = 1, sides = 6) {
  return Array.from({ length: count }, () =>
    Math.floor(Math.random() * sides) + 1
  );
}

// Visual dice with CSS
.die {
  width: 48px; height: 48px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  display: grid;
  grid-template: repeat(3, 1fr) / repeat(3, 1fr);
  padding: 6px;
}
.pip {
  width: 8px; height: 8px;
  background: #333;
  border-radius: 50%;
  align-self: center;
  justify-self: center;
}
```

### Drag and drop

```javascript
// For piece movement
let dragState = null;

element.addEventListener('dragstart', (e) => {
  dragState = { piece: e.target.dataset.piece, from: getPosition(e.target) };
});

dropZone.addEventListener('drop', (e) => {
  const to = getPosition(e.target);
  const move = { piece: dragState.piece, from: dragState.from, to };
  if (getValidMoves(gameState).some(m => movesEqual(m, move))) {
    makeMove(move);
  }
  dragState = null;
});
```

### Timer / clock (for timed games)

```javascript
function createClock(timePerPlayer) {
  const clocks = players.map(() => timePerPlayer);
  let activePlayer = 0;
  let interval = null;

  return {
    start(player) {
      activePlayer = player;
      interval = setInterval(() => {
        clocks[activePlayer] -= 1;
        if (clocks[activePlayer] <= 0) {
          // Time's up for this player
          clearInterval(interval);
          handleTimeout(activePlayer);
        }
        renderClocks(clocks);
      }, 1000);
    },
    switchTo(player) {
      clearInterval(interval);
      this.start(player);
    },
    pause() { clearInterval(interval); },
    getTime(player) { return clocks[player]; }
  };
}
```

### AI opponent (minimax)

```javascript
function minimax(state, depth, maximizing, alpha = -Infinity, beta = Infinity) {
  if (depth === 0 || isGameOver(state)) {
    return { score: evaluate(state) };
  }

  const moves = getValidMoves(state);
  let best = { score: maximizing ? -Infinity : Infinity };

  for (const move of moves) {
    const next = applyMove(state, move);
    const result = minimax(next, depth - 1, !maximizing, alpha, beta);

    if (maximizing) {
      if (result.score > best.score) best = { score: result.score, move };
      alpha = Math.max(alpha, result.score);
    } else {
      if (result.score < best.score) best = { score: result.score, move };
      beta = Math.min(beta, result.score);
    }
    if (beta <= alpha) break; // Prune
  }
  return best;
}

function aiMove(state, difficulty = 3) {
  const { move } = minimax(state, difficulty, true);
  return move;
}
```

### Undo system

```javascript
function undo() {
  if (gameState.history.length === 0) return false;
  const prev = gameState.history.pop();
  gameState = prev.state;
  gameState.validMoves = getValidMoves(gameState);
  render(gameState);
  return true;
}
```

## Visual design and data attributes

For CSS variable system, color palettes, typography, responsive design, animations, and data attributes for testing, see [VISUAL.md](VISUAL.md).
