# Board Game Multiplayer Architecture

## Play mode hierarchy

Every game should support as many of these modes as the game allows, in this priority order:

| Mode | Description | Hidden info? | Network? | Best for |
|------|-------------|-------------|----------|----------|
| **Local hot-seat** | Players share one screen, take turns | Screen-transition between turns | No | Quick play, simple games |
| **Local split-tab** | Each player opens a tab in the same browser | Full support via BroadcastChannel | No (same browser) | Games with hidden hands/info |
| **Online P2P** | Players on different devices, WebRTC | Full support | Yes (P2P) | Remote play |
| **vs AI** | Human vs computer opponent | N/A | No | Solo practice |

Not every game needs every mode. A game with no hidden information (Chess, Go) only needs hot-seat + online. A game with hidden info (Poker, Scrabble) benefits from all modes.

## Mode selection UI

The game starts with a lobby screen before the board appears:

```html
<div id="lobby">
  <h1>[Game Name]</h1>
  <div class="mode-buttons">
    <button data-mode="local">Local Game (Hot-Seat)</button>
    <button data-mode="online-host">Host Online Game</button>
    <button data-mode="online-join">Join Online Game</button>
    <button data-mode="ai">Play vs AI</button>
  </div>

  <!-- Player config (shown for local/AI) -->
  <div id="player-config" hidden>
    <label>Number of players: <select id="player-count">...</select></label>
    <div id="player-names">...</div>
    <button id="start-game">Start Game</button>
  </div>

  <!-- Online host view -->
  <div id="host-view" hidden>
    <p>Room code: <strong id="room-code">----</strong></p>
    <p>Share this code with other players.</p>
    <div id="connected-players"></div>
    <button id="start-online" disabled>Start Game</button>
  </div>

  <!-- Online join view -->
  <div id="join-view" hidden>
    <label>Enter room code: <input id="room-input" maxlength="6"></label>
    <button id="join-btn">Join</button>
    <p id="join-status"></p>
  </div>
</div>
```

## Architecture: host-authoritative model

One client (the "host") owns the authoritative game state. All other clients are "guests" that send move requests and receive state updates. This applies to both online P2P and local split-tab modes.

```
┌──────────┐     move request     ┌──────────┐
│  Guest A ├─────────────────────►│          │
│ (player) │◄─────────────────────┤   Host   │
│          │     state update     │(authority)│
└──────────┘                      │          │
                                  │  - owns gameState
┌──────────┐     move request     │  - validates moves
│  Guest B ├─────────────────────►│  - computes validMoves
│ (player) │◄─────────────────────┤  - broadcasts updates
│          │     state update     │          │
└──────────┘                      └──────────┘
```

### Why host-authoritative?

- **Single source of truth**: No state divergence or conflict resolution needed
- **Cheat prevention**: Only the host validates moves — guests can't forge state
- **Simplicity**: One validation path, one state machine
- **Hidden information**: Host controls exactly what each player sees

## Game state model (multiplayer-aware)

Extend the base game state with multiplayer fields:

```javascript
window.gameState = {
  // --- core (same as single-player) ---
  phase: "lobby" | "playing" | "gameOver",
  currentPlayer: 0,
  players: [{
    id: 0,
    name: "Player 1",
    score: 0,
    connected: true,     // online: is this player connected?
    isLocal: true,       // is this player on this device?
    isAI: false,
    // game-specific: hand, pieces, resources, etc.
  }],
  board: null,
  turnNumber: 0,
  history: [],
  validMoves: [],
  winner: null,
  config: {},

  // --- multiplayer additions ---
  mode: "local" | "online" | "ai",
  localPlayerId: 0,       // which player THIS client controls
  roomCode: null,          // online: room identifier
  hostId: null,            // online: peer ID of the host
  isHost: false,           // is this client the host?
  turnTimer: null,         // optional: seconds remaining for current turn
  turnTimeLimit: 0,        // 0 = no limit
};
```

## Hidden information management

Many board games have information that only some players should see (card hands, face-down tiles, secret objectives). The host must never send another player's private data.

### Player view function

The host computes a **player-specific view** before sending state updates:

```javascript
function getPlayerView(state, playerId) {
  return {
    phase: state.phase,
    currentPlayer: state.currentPlayer,
    turnNumber: state.turnNumber,
    winner: state.winner,
    board: getVisibleBoard(state, playerId),   // hide face-down info
    players: state.players.map((p, i) => ({
      id: p.id,
      name: p.name,
      score: p.score,
      connected: p.connected,
      isAI: p.isAI,
      // Show own private info, hide others'
      ...(i === playerId
        ? { hand: p.hand, resources: p.resources }
        : { handCount: p.hand?.length ?? 0 }),
    })),
    // Only send valid moves for THIS player, and only on their turn
    validMoves: state.currentPlayer === playerId
      ? getValidMoves(state)
      : [],
    lastMove: state.history[state.history.length - 1]?.move ?? null,
  };
}
```

### Hot-seat hidden info: turn transition screen

For local hot-seat with hidden info, show a transition screen between turns:

```javascript
function showTurnTransition(nextPlayerName) {
  // Overlay that hides the board
  const overlay = document.getElementById('turn-transition');
  overlay.innerHTML = `
    <h2>Pass the device to ${nextPlayerName}</h2>
    <button onclick="dismissTransition()">I'm ${nextPlayerName} — Show My Turn</button>
  `;
  overlay.hidden = false;
}

function dismissTransition() {
  document.getElementById('turn-transition').hidden = true;
  render(getPlayerView(gameState, gameState.currentPlayer));
}
```

## Communication layer

### Layer 1: BroadcastChannel (local split-tab)

Zero-dependency, same-origin communication between browser tabs:

```javascript
class LocalChannel {
  constructor(roomCode, onMessage) {
    this.channel = new BroadcastChannel(`game-${roomCode}`);
    this.channel.onmessage = (e) => onMessage(e.data);
  }

  send(msg) {
    this.channel.postMessage(msg);
  }

  close() {
    this.channel.close();
  }
}
```

**How local split-tab works:**
1. Host tab creates the game, generates a room code
2. Guest tabs open the same HTML file and enter the room code
3. All tabs communicate via BroadcastChannel
4. Each tab shows only its player's view (hidden info supported)

### Layer 2: WebRTC via PeerJS (online P2P)

PeerJS wraps WebRTC with a free public signaling server. Load from CDN — no install needed:

```html
<script src="https://unpkg.com/peerjs@1/dist/peerjs.min.js"></script>
```

```javascript
class OnlineChannel {
  constructor(isHost, roomCode, onMessage, onPlayerJoin, onPlayerLeave) {
    this.isHost = isHost;
    this.connections = new Map(); // peerId -> DataConnection
    this.onMessage = onMessage;

    if (isHost) {
      // Host creates a peer with a predictable ID derived from room code
      this.peer = new Peer(`boardgame-${roomCode}`);
      this.peer.on('connection', (conn) => {
        this._setupConn(conn);
        onPlayerJoin(conn.peer);
      });
    } else {
      // Guest creates a random peer and connects to the host
      this.peer = new Peer();
      this.peer.on('open', () => {
        const conn = this.peer.connect(`boardgame-${roomCode}`, { reliable: true });
        this._setupConn(conn);
      });
    }
  }

  _setupConn(conn) {
    conn.on('open', () => {
      this.connections.set(conn.peer, conn);
    });
    conn.on('data', (data) => {
      this.onMessage(data, conn.peer);
    });
    conn.on('close', () => {
      this.connections.delete(conn.peer);
    });
  }

  // Send to a specific peer
  sendTo(peerId, msg) {
    this.connections.get(peerId)?.send(msg);
  }

  // Broadcast to all connected peers
  broadcast(msg) {
    for (const conn of this.connections.values()) {
      conn.send(msg);
    }
  }

  close() {
    this.peer.destroy();
  }
}
```

### Unified network interface

Wrap both channel types behind a common interface so the game logic doesn't care about the transport:

```javascript
class NetworkManager {
  constructor() {
    this.channel = null;
    this.isHost = false;
    this.playerId = 0;
    this.onStateUpdate = null;    // guest: called when host sends new state
    this.onMoveRequest = null;    // host: called when guest requests a move
    this.onPlayerJoin = null;
    this.onPlayerLeave = null;
  }

  hostGame(mode, roomCode) {
    this.isHost = true;
    this.playerId = 0;
    if (mode === 'online') {
      this.channel = new OnlineChannel(true, roomCode,
        (msg, from) => this._handleHostMessage(msg, from),
        (peerId) => this.onPlayerJoin?.(peerId),
        (peerId) => this.onPlayerLeave?.(peerId),
      );
    } else if (mode === 'local-split') {
      this.channel = new LocalChannel(roomCode,
        (msg) => this._handleHostMessage(msg, msg.from),
      );
    }
  }

  joinGame(mode, roomCode) {
    this.isHost = false;
    if (mode === 'online') {
      this.channel = new OnlineChannel(false, roomCode,
        (msg) => this._handleGuestMessage(msg),
        () => {},
        () => {},
      );
    } else if (mode === 'local-split') {
      this.channel = new LocalChannel(roomCode,
        (msg) => this._handleGuestMessage(msg),
      );
    }
  }

  // Guest -> Host: request a move
  requestMove(move) {
    if (this.isHost) {
      // Host is also a player — process locally
      this.onMoveRequest?.({ playerId: this.playerId, move }, null);
    } else {
      this.channel.send({
        type: 'moveRequest',
        playerId: this.playerId,
        move,
      });
    }
  }

  // Host -> All guests: broadcast player-specific state
  broadcastState(state, getPlayerView) {
    if (!this.isHost) return;
    // Send each guest their own view
    for (const [peerId, playerId] of this.peerPlayerMap) {
      const view = getPlayerView(state, playerId);
      this.channel.sendTo(peerId, {
        type: 'stateUpdate',
        state: view,
      });
    }
  }

  _handleHostMessage(msg, from) {
    if (msg.type === 'moveRequest') {
      this.onMoveRequest?.(msg, from);
    } else if (msg.type === 'join') {
      this.onPlayerJoin?.(from, msg);
    }
  }

  _handleGuestMessage(msg) {
    if (msg.type === 'stateUpdate') {
      this.onStateUpdate?.(msg.state);
    } else if (msg.type === 'gameStart') {
      this.onStateUpdate?.(msg.state);
    } else if (msg.type === 'error') {
      console.error('Host rejected move:', msg.error);
    }
  }
}
```

## Message protocol

All messages are JSON objects with a `type` field:

### Guest -> Host

| Type | Fields | Purpose |
|------|--------|---------|
| `join` | `{ type, playerName }` | Request to join the game |
| `moveRequest` | `{ type, playerId, move }` | Request to make a move |
| `ping` | `{ type }` | Keep-alive |

### Host -> Guest

| Type | Fields | Purpose |
|------|--------|---------|
| `welcome` | `{ type, playerId, roomCode, players }` | Confirm join, assign player ID |
| `stateUpdate` | `{ type, state }` | Player-specific game state after a move |
| `gameStart` | `{ type, state }` | Game is starting, here's your initial view |
| `error` | `{ type, error }` | Move rejected or other error |
| `playerJoined` | `{ type, playerName, playerCount }` | Notify lobby of new player |
| `playerLeft` | `{ type, playerId }` | Notify of disconnection |

## Host-side move processing

When the host receives a move request:

```javascript
function handleMoveRequest(msg, fromPeer) {
  const { playerId, move } = msg;

  // 1. Verify it's this player's turn
  if (gameState.currentPlayer !== playerId) {
    sendError(fromPeer, "Not your turn");
    return;
  }

  // 2. Validate the move
  const validMoves = getValidMoves(gameState);
  if (!validMoves.some(m => movesEqual(m, move))) {
    sendError(fromPeer, "Invalid move");
    return;
  }

  // 3. Apply the move
  gameState.history.push({ move, player: playerId });
  gameState = applyMove(gameState, move);
  gameState.turnNumber++;
  gameState.currentPlayer = getNextPlayer(gameState);
  gameState.validMoves = getValidMoves(gameState);

  // 4. Check win condition
  const winner = checkWinCondition(gameState);
  if (winner !== null) {
    gameState.phase = 'gameOver';
    gameState.winner = winner;
  }

  // 5. Broadcast player-specific views to all clients
  broadcastStateToAll();

  // 6. Update host's own UI
  render(getPlayerView(gameState, 0));

  // 7. If next player is AI, trigger AI move
  if (gameState.players[gameState.currentPlayer]?.isAI) {
    setTimeout(() => {
      const aiMoveChoice = aiMove(gameState);
      handleMoveRequest({ playerId: gameState.currentPlayer, move: aiMoveChoice }, null);
    }, 500);
  }
}
```

## Turn order and complex turns

### Simple alternating turns

```javascript
function getNextPlayer(state) {
  let next = (state.currentPlayer + 1) % state.players.length;
  // Skip eliminated/disconnected players
  while (state.players[next].eliminated || !state.players[next].connected) {
    next = (next + 1) % state.players.length;
    if (next === state.currentPlayer) break; // All others gone
  }
  return next;
}
```

### Multi-phase turns

Some games have turns with multiple phases (e.g., roll dice -> move -> buy/trade -> end turn):

```javascript
// Turn phases for complex games
const TURN_PHASES = {
  ROLL: 'roll',
  MOVE: 'move',
  ACTION: 'action',     // buy, trade, play card, etc.
  END: 'end',
};

// State includes current turn phase
gameState.turnPhase = TURN_PHASES.ROLL;

function getValidMoves(state) {
  switch (state.turnPhase) {
    case TURN_PHASES.ROLL:
      return [{ type: 'roll' }];
    case TURN_PHASES.MOVE:
      return getMovementOptions(state);
    case TURN_PHASES.ACTION:
      return [...getActionOptions(state), { type: 'endTurn' }];
    case TURN_PHASES.END:
      return [{ type: 'endTurn' }];
  }
}

function applyMove(state, move) {
  const next = cloneState(state);
  switch (move.type) {
    case 'roll':
      next.lastRoll = rollDice(2);
      next.turnPhase = TURN_PHASES.MOVE;
      break;
    case 'move':
      // Apply movement
      next.turnPhase = TURN_PHASES.ACTION;
      break;
    case 'endTurn':
      next.turnPhase = TURN_PHASES.ROLL;
      next.currentPlayer = getNextPlayer(next);
      break;
    // ... game-specific actions
  }
  return next;
}
```

### Simultaneous action selection

Some games have all players act simultaneously (e.g., secret bid, card selection):

```javascript
gameState.pendingActions = {}; // playerId -> action (null if not yet chosen)

function submitAction(playerId, action) {
  gameState.pendingActions[playerId] = action;

  // Check if all players have submitted
  const allSubmitted = gameState.players.every(
    p => p.eliminated || gameState.pendingActions[p.id] != null
  );

  if (allSubmitted) {
    resolveSimultaneousActions(gameState);
    gameState.pendingActions = {};
    gameState.turnNumber++;
  }
}
```

For simultaneous actions online, the host collects all submissions, then resolves and broadcasts once all are in.

## Turn timer (optional)

For games that benefit from time pressure:

```javascript
let turnTimerInterval = null;

function startTurnTimer(seconds) {
  gameState.turnTimer = seconds;
  clearInterval(turnTimerInterval);
  turnTimerInterval = setInterval(() => {
    gameState.turnTimer--;
    renderTimer(gameState.turnTimer);
    if (gameState.turnTimer <= 0) {
      clearInterval(turnTimerInterval);
      handleTurnTimeout();
    }
  }, 1000);
}

function handleTurnTimeout() {
  // Options: auto-pass, random legal move, or forfeit
  const validMoves = getValidMoves(gameState);
  if (validMoves.some(m => m.type === 'pass')) {
    handleMoveRequest({ playerId: gameState.currentPlayer, move: { type: 'pass' } });
  } else if (validMoves.length > 0) {
    // Force a random legal move
    const forced = validMoves[Math.floor(Math.random() * validMoves.length)];
    handleMoveRequest({ playerId: gameState.currentPlayer, move: forced });
  }
}
```

## Reconnection handling

When a player disconnects during an online game:

```javascript
function handlePlayerDisconnect(playerId) {
  gameState.players[playerId].connected = false;

  // If it was their turn, auto-advance
  if (gameState.currentPlayer === playerId) {
    // Option 1: Skip to next player
    gameState.currentPlayer = getNextPlayer(gameState);
    gameState.validMoves = getValidMoves(gameState);
    broadcastStateToAll();

    // Option 2: Pause and wait for reconnect
    // gameState.phase = 'paused';
    // broadcastStateToAll();
  }

  // Notify remaining players
  broadcastPlayerLeft(playerId);
}

function handlePlayerReconnect(playerId, peerConn) {
  gameState.players[playerId].connected = true;

  // Send them the current state
  const view = getPlayerView(gameState, playerId);
  peerConn.send({ type: 'stateUpdate', state: view });

  // Notify others
  broadcastPlayerRejoined(playerId);
}
```

## Room code generation

```javascript
function generateRoomCode(length = 4) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // no I/O/0/1 to avoid confusion
  let code = '';
  for (let i = 0; i < length; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}
```

## render_game_to_text (multiplayer-aware)

The test API must reflect multiplayer state:

```javascript
window.render_game_to_text = function() {
  return JSON.stringify({
    phase: gameState.phase,
    mode: gameState.mode,
    currentPlayer: gameState.currentPlayer,
    localPlayerId: gameState.localPlayerId,
    turnNumber: gameState.turnNumber,
    turnPhase: gameState.turnPhase ?? null,
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

## Choosing which modes to implement

Use this decision tree:

```
Does the game have hidden information (hands, face-down cards, secret roles)?
├─ NO (Chess, Go, Checkers, etc.)
│   ├─ Implement: local hot-seat + online P2P + AI
│   └─ Hot-seat needs NO transition screen
│
└─ YES (Poker, Scrabble, Battleship, etc.)
    ├─ Implement: local hot-seat (with transition) + local split-tab + online P2P + AI
    └─ Hot-seat MUST have turn transition screen to hide hands
        Split-tab gives each player their own window (better UX for hidden info)

Does the game support > 2 players?
├─ NO (Chess, Battleship, etc.)
│   └─ Player config is simple: names only
│
└─ YES (Risk, Catan, Uno, etc.)
    └─ Add player count selector (min to max per game rules)
        Allow mix of human and AI players

Does the game have simultaneous actions?
├─ NO (most turn-based games)
│   └─ Standard turn rotation
│
└─ YES (Rock-Paper-Scissors, auction phases, etc.)
    └─ Implement pending action collection
        All players submit secretly, then resolve together
```
