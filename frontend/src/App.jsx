import { useEffect, useMemo, useRef, useState } from "react";
import WebSocketAsPromised from "websocket-as-promised";
import { defaultDarkModeOverride, Button, Card, Flex, Grid, Input, Text, ThemeProvider } from "@aws-amplify/ui-react";
import "@chatscope/chat-ui-kit-styles/dist/default/styles.min.css";
import "./components/mystyles.css";
import { MainContainer, ChatContainer, MessageList, MessageInput } from "@chatscope/chat-ui-kit-react";
import MyMessage from "./components/MyMessage";
import MyVotingForm from "./components/MyVotingForm";
import VizAvalon from "./components/VizAvalon";
import QuestBoard from "./components/QuestBoard";
import "./components/mystyles.css";
import TeamSelector from "./components/TeamSelector";

const HOST_NAME = "10.50.68.252"; // Alternatively, localhost o 10.50.68.252

const STAGE = {
  REVEAL: "RevealingRoles",
  SELECT_TEAM: "SelectingTeam",
  VOTE_TEAM: "VotingTeam",
  VOTE_QUEST: "VotingQuest",
  TEAM_VOTED: "TeamVoted",
  QUEST_VOTED: "QuestVoted",
};

const theme = { name: "my-theme", overrides: [defaultDarkModeOverride] };

// 👇 Helper para "inventar" el mensaje de propuesta de equipo cuando venga de un bot
function enrichTeamMessage(msg) {
  if (!msg) return msg;

  // Si ya trae message, no tocamos nada
  if (msg.message && msg.message.trim() !== "") return msg;

  // Si trae un array de team, lo interpretamos como propuesta de equipo
  if (Array.isArray(msg.team) && msg.team.length > 0) {
    // ¿Quién es el líder?
    // En tu payload humano usas `index`, pero el backend podría usar `leader`.
    const leaderIdx =
      typeof msg.index === "number"
        ? msg.index
        : typeof msg.leader === "number"
        ? msg.leader
        : null;

    const teamStr = `[${msg.team.join(", ")}]`;

    const leaderText =
      leaderIdx !== null ? `Player ${leaderIdx}` : "A bot";

    const text = `${leaderText} proposes the following team ${teamStr}`;

    return {
      ...msg,
      message: text,
    };
  }

  // Si no hay team ni message, lo dejamos igual
  return msg;
}


export default function App() {

  const [playerNames, setPlayerNames] = useState(
    () => Array.from({ length: 10 }, (_, i) => `player-${i}`)
  );

  const handleRenamePlayer = (index, newName) => {
    setPlayerNames(prev => {
      const next = [...prev];
      // si ponen vacío, volvemos al nombre por defecto
      next[index] = newName && newName.trim() !== "" ? newName.trim() : `player-${index}`;
      return next;
    });
  };


  const [role, setRole] = useState("");
  const [knownEvil, setKnownEvil] = useState([]);
  const [isGuessingMerlin, setIsGuessingMerlin] = useState(false);
  const [vote, setVote] = useState(null);

  const [numHumans, setNumHumans] = useState(1);
  const [numBots, setNumBots] = useState(4);
  const totalPlayers = numHumans + numBots; // ya está garantizado <= 10


  // toggles específicos de VizAvalon
  const [showVotesViz, setShowVotesViz] = useState(false);
  const [showQuestsViz, setShowQuestsViz] = useState(false);


  const [messages, setMessages] = useState([]); // [{message, index, action?}]
  const wspRef = useRef(null);
  const gameState = useRef({ index: undefined, role: undefined, stage: undefined });

  const [showAnalytics, setShowAnalytics] = useState(true);

  const [debugSelectedTeam, setDebugSelectedTeam] = useState([]);

  // 💡 Cambia esto a false cuando ya no quieras el truco
  const FORCE_MERLIN_FOR_TEST = false;

  const [wsPath, setWsPath] = useState(null);     // e.g. "/ws/Hs2x3Y"
  const [gameIdInput, setGameIdInput] = useState(""); // texto del input

  const [availableGames, setAvailableGames] = useState([]); // lista de "/ws/<id>"

  // ====== Cargar lista de juegos activos desde el backend ======
  const refreshGames = async () => {
    try {
      const resp = await fetch(`http://${HOST_NAME}:8888/games`);
      const data = await resp.json(); // esperamos algo como ["/ws/abc", "/ws/xyz"]
      console.log("[refreshGames] games:", data);
      setAvailableGames(data || []);
    } catch (err) {
      console.error("[refreshGames] error:", err);
    }
  };


  const debugHistory = [
    {
      leader: "player-0",
      team: ["player-0", "player-1"],
      votes: [
        { player: "player-0", vote: "yes" },
        { player: "player-1", vote: "yes" },
        { player: "player-2", vote: "yes" },
        { player: "player-3", vote: "yes" },
        { player: "player-4", vote: "yes" },
      ],
      team_vote_outcome: "succeeded", // el equipo fue aceptado
      quest_vote_outcome: "failed",   // pero la misión falló
    },
  ];

  const debugPlayerNames = [
    "Yangus",
    "Jessica",
    "Angelo",
    "Valentina",
    "Medea",
  ];

  const [isSelectingTeam, setIsSelectingTeam] = useState(false);
  const [requiredTeamSize, setRequiredTeamSize] = useState(2);

  const [useDebugViz, setUseDebugViz] = useState(false);

  useEffect(() => {
    console.log("[App] messages snapshot:", messages);
  }, [messages]);

  useEffect(() => {
    refreshGames();
  }, []);

// Normaliza el rol a string en minúsculas (por si jsonpickle manda objetos raros)
function normalizeRole(r) {
  if (typeof r === "string") {
    return r.toLowerCase();
  }
  if (r && typeof r.name === "string") {
    return r.name.toLowerCase();
  }
  return String(r).toLowerCase();
}

  // ===== Helpers para parsing de mensajes a "history" (Viz-ready) =====
  const vizHistory = useMemo(() => {
    const rounds = [];
    let holder = null;

    // jugadores internos tipo "player-0"... basados en el estado actual
    const totalPlayers = numHumans + numBots;
    const allPlayers = Array.from(
      { length: totalPlayers },
      (_, i) => `player-${i}`
    );

    const pushHolder = () => {
      if (!holder) return;

      // Si nunca logramos inferir el team, usamos todos los jugadores
      if (!holder.team || holder.team.length === 0) {
        holder.team = [...allPlayers];
      }

      rounds.push(holder);
      holder = null;
    };

    for (const m of messages) {
      const text = m?.message || "";
      if (!text) continue;

      console.log("[vizParser] processing:", text, "action:", m.action, "index:", m.index);

      // 1) Intento de detectar propuesta de equipo (por si el backend sigue mandándola)
      //    "Player i proposes the following team [a,b]"
      const prop = text.match(/Player\s+(\d+)\s+proposes.*\[(.+)\]/i);
      if (prop) {
        const leaderIdx = Number(prop[1]);
        const rawTeam = prop[2];

        const team = rawTeam
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s !== "")
          .map((s) => `player-${Number(s)}`);

        console.log("[vizParser] NEW ROUND (from proposal) leader =", leaderIdx, "team =", team);

        // cerramos ronda previa (si existe)
        pushHolder();

        holder = {
          leader: `player-${leaderIdx}`,
          team,
          votes: [],
          team_vote_outcome: undefined,
          quest_vote_outcome: undefined,
        };
        continue;
      }

      // 2) Si el backend mandara team/leader como campos estructurados
      //    (por ejemplo en algún mensaje con action === "TeamSelected")
      if (!holder && Array.isArray(m.team)) {
        const leaderIdx = typeof m.leader === "number" ? m.leader : null;
        const team = m.team.map((idx) => `player-${idx}`);

        console.log("[vizParser] NEW ROUND (from structured msg) leader =", leaderIdx, "team =", team);

        pushHolder();

        holder = {
          leader: leaderIdx !== null ? `player-${leaderIdx}` : null,
          team,
          votes: [],
          team_vote_outcome: undefined,
          quest_vote_outcome: undefined,
        };
        // seguimos procesando el mismo texto por si además matchea otros patrones
      }

      // 3) Votos al equipo
      //    Ej: "Player 0 voted 'True' on team"
      //        "Player 4 voted 'yes' on team"
      const vteam = text.match(
        /^Player\s+(\d+)\s+voted\s+'?(\w+)'?\s*(?:on\s+team)?/i
      );
      if (vteam) {
        // si aún no hay holder, empezamos una ronda solo con base en los votos
        if (!holder) {
          console.log("[vizParser] starting holder from team vote");
          holder = {
            leader: null,
            team: [],
            votes: [],
            team_vote_outcome: undefined,
            quest_vote_outcome: undefined,
          };
        }

        const playerIdx = Number(vteam[1]);
        const voteRaw = vteam[2];

        const player = `player-${playerIdx}`;
        const isYes = /^(true|yes|y|1)$/i.test(String(voteRaw));

        const filtered = (holder.votes || []).filter((v) => v.player !== player);
        holder.votes = [
          ...filtered,
          { player, vote: isYes ? "yes" : "no" },
        ];

        console.log("[vizParser] VOTE", player, "=", isYes ? "yes" : "no");
        continue;
      }

      // 4) Equipo aceptado
      if (text === "Team accepted!" && holder) {
        holder.team_vote_outcome = "succeeded";
        console.log("[vizParser] TEAM ACCEPTED");
        continue;
      }

      // 5) Resultado de misión: "Quest result True/False"
      const q = text.match(/Quest result\s+(True|False)/i);
      if (q && holder) {
        const ok = q[1].toLowerCase() === "true";
        holder.quest_vote_outcome = ok ? "succeeded" : "failed";
        console.log(
          "[vizParser] QUEST RESULT =",
          ok ? "succeeded" : "failed"
        );
        // fin de ronda
        pushHolder();
        continue;
      }

      // 6) Rechazo de equipo inferido
      if (text.startsWith("Asked Player") && text.includes("to select a team")) {
        if (holder && !holder.team_vote_outcome) {
          holder.team_vote_outcome = "failed";
          console.log("[vizParser] TEAM REJECTED (inferred)");
          pushHolder();
        }
        continue;
      }
    }

    // Cerrar última ronda si quedó abierta
    pushHolder();

    console.log("[App] vizHistory length =", rounds.length, rounds);
    return rounds;
  }, [messages, numHumans, numBots]);




  // ===== Historial filtrado: ocultar la ronda actual (incompleta) =====
  const vizHistoryClosed = useMemo(() => {
    if (!vizHistory || vizHistory.length === 0) return vizHistory;

    const last = vizHistory[vizHistory.length - 1];

    const hasQuestOutcome =
      last.quest_vote_outcome === "succeeded" ||
      last.quest_vote_outcome === "failed";

    const isRejected = last.team_vote_outcome === "failed";

    // Si la última ronda está abierta (sin quest y no fue rechazada),
    // la ocultamos (nos quedamos con todas menos la última).
    if (!hasQuestOutcome && !isRejected) {
      return vizHistory.slice(0, -1);
    }

    // Si ya está cerrada, usamos todo el historial
    return vizHistory;
  }, [vizHistory]);




  const wrapperSetVote = (value) => setVote(value);

  // ====== Crear juego (observador / host) ======
  const createNewGame = async () => {
    // Cerramos WS previo si hubiera
    if (wspRef.current) {
      try { await wspRef.current.close(); } catch {}
      wspRef.current = null;
    }

    const totalPlayers = numHumans + numBots;

    // 1) Crear juego en el backend
    const resp = await fetch(`http://${HOST_NAME}:8888/games`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nplayers: totalPlayers,
        nbots: numBots,
      }),
    });

    const data = await resp.json(); // { location: "/ws/<gameid>" }
    console.log("[createNewGame] backend response:", data);

    const location = data.location;        // "/ws/Hs2x3Y..."
    const gameId = location.split("/").pop(); // "Hs2x3Y..."

    // Guardamos en estado
    setWsPath(location);
    setGameIdInput(gameId);   // para que el host vea el código y pueda compartirlo

    // Opcional: refrescar la lista de partidas disponibles
    refreshGames();


    // 2) Conectar como observador/host a ESA sala específica
    const wsp = new WebSocketAsPromised(`ws://${HOST_NAME}:8888${location}`);
    await wsp.open();
    wspRef.current = wsp;

    wsp.onMessage.addListener((data) => {
      const raw = JSON.parse(data);
      console.log("[WS/createNewGame] raw msg:", raw);

      const msg = enrichTeamMessage(raw);

      setMessages((prev) => [...prev, msg]);
    });
  };


  // ====== Unirse como jugador a una sala específica ======
  const joinGame = async (gameIdOverride) => {
    // Si nos pasan un ID directo (por botón), usamos ese; si no, usamos el input
    const rawId = gameIdOverride != null ? gameIdOverride : gameIdInput;
    const trimmedId = String(rawId).trim();

    if (!trimmedId) {
      console.error("[joinGame] No game id provided");
      return;
    }

    const location = `/ws/${trimmedId}`;
    setWsPath(location);

    if (wspRef.current) {
      try {
        await wspRef.current.close();
      } catch {}
      wspRef.current = null;
    }

    const wsp = new WebSocketAsPromised(`ws://${HOST_NAME}:8888${location}`);
    await wsp.open();
    wspRef.current = wsp;

    wsp.onMessage.addListener((data) => {
      // 1) Parseamos SIEMPRE primero
      const raw = JSON.parse(data);
      console.log("[WS/joinGame] raw msg:", raw);

      // 2) Enriquecemos el mensaje (para propuestas de equipo de bots)
      const msg = enrichTeamMessage(raw);

      // 3) Manejo especial de RevealRoles
      if (msg.action === "RevealRoles") {
        const myIndex = msg.index;
        const allRoles = msg.roles || [];

        const myRole = allRoles[myIndex];

        gameState.current = {
          index: myIndex,
          role: myRole,
          stage: STAGE.REVEAL,
        };

        setRole(myRole);

        const myRoleNorm = normalizeRole(myRole);

        let evilIndices = [];

        if (myRoleNorm === "merlin") {
          evilIndices = allRoles
            .map((r, i) => ({ i, r: normalizeRole(r) }))
            .filter(({ i, r }) => r === "evil" && i !== myIndex)
            .map(({ i }) => i);

          setKnownEvil(evilIndices);
          console.log("[RevealRoles] As Merlin I see evil players:", evilIndices);
        } else {
          setKnownEvil([]);
        }

        setMessages((prev) => {
          const next = [
            ...prev,
            msg,
            {
              message: `I am Player ${myIndex}, with role '${myRole}'`,
              index: -1,
              action: "LocalInfo",
            },
          ];

          if (myRoleNorm === "merlin" && evilIndices.length > 0) {
            const evilNames = evilIndices
              .map((idx) => playerNames[idx] || `player-${idx}`)
              .join(", ");

            next.push({
              message: `As Merlin, you know evil players are: ${evilNames}`,
              index: -1,
              action: "LocalInfo",
            });
          }

          return next;
        });

        return;
      }

      // 4) Resto de acciones del servidor
      if (msg.action === "VoteTeam") {
        gameState.current.stage = STAGE.VOTE_TEAM;
        setVote(null);
      } else if (msg.action === "VoteQuest") {
        gameState.current.stage = STAGE.VOTE_QUEST;
        setVote(null);
      } else if (msg.action === "SelectTeam") {
        console.log(">>> Received SelectTeam message:", msg);

        gameState.current.stage = STAGE.SELECT_TEAM;

        let teamSize = 2;
        if (typeof msg.team_size === "number" && msg.team_size > 0) {
          teamSize = msg.team_size;
        } else {
          const match = msg.message?.match(/team with (\d+) members?/i);
          if (match) {
            const parsed = Number(match[1]);
            if (!Number.isNaN(parsed) && parsed > 0) {
              teamSize = parsed;
            }
          }
        }

        console.log(">>> final teamSize:", teamSize);
        setRequiredTeamSize(teamSize);
        setIsSelectingTeam(true);
      }

      // 5) Guardar mensaje en el chat
      setMessages((prev) => [...prev, msg]);
    });
  };




  // ====== Enviar acciones ======
  const sendMessage = (message) => {
    if (!wspRef.current) return;
    const payload = {
      index: gameState.current.index,
      message,
    };

    if (gameState.current.stage === STAGE.VOTE_TEAM) {
      payload.vote = vote === "yes";
      payload.event = "TeamVoted";
      gameState.current.stage = STAGE.TEAM_VOTED;
    } else if (gameState.current.stage === STAGE.VOTE_QUEST) {
      payload.vote = vote === "yes";
      payload.event = "QuestVoted";
      gameState.current.stage = STAGE.QUEST_VOTED;
    } else if (gameState.current.stage === STAGE.SELECT_TEAM) {
      // Por ahora seguimos aceptando JSON textual: "[0,1]" etc.
      try {
        payload.team = JSON.parse(message);
        payload.message = `Player ${payload.index} proposes the following team ${message}`;
        payload.event = "TeamSelected";
      } catch {
        // ignora si no es JSON válido
        return;
      }
    }

    wspRef.current.send(JSON.stringify(payload));
  };

  const castVote = () =>
    sendMessage(
      `Player ${gameState.current.index} voted${
        gameState.current.stage === STAGE.VOTE_TEAM ? ` '${vote}' on team` : ""
      }`
    );

  const votingFormIfNeeded = () => {
    if (gameState.current.stage === STAGE.VOTE_TEAM) {
      return (
        <MyVotingForm
          legend="Vote on the proposed team"
          negativeEnabled={role === "evil"}
          vote={vote}
          setVote={wrapperSetVote}
          onSubmit={castVote}
        />
      );
    }
    if (gameState.current.stage === STAGE.VOTE_QUEST) {
      return (
        <MyVotingForm
          legend="Vote on quest outcome"
          negativeEnabled={role === "evil"}
          vote={vote}
          setVote={wrapperSetVote}
          onSubmit={castVote}
        />
      );
    }
    return null;
  };

  const handleTeamConfirm = (indices) => {
    if (!wspRef.current) return;

    // indices son [0,1,3,...] → IDs internos de jugador
    const team = indices;

    const payload = {
      index: gameState.current.index,
      team,
      event: "TeamSelected",
      message: `Player ${gameState.current.index} proposes the following team [${team.join(",")}]`,
    };

    console.log(">>> sending TeamSelected payload:", payload);

    // dejamos que el servidor cambie el stage cuando responda
    wspRef.current.send(JSON.stringify(payload));
    setIsSelectingTeam(false);
  };


  useEffect(() => {
    return () => {
      if (wspRef.current) {
        try { wspRef.current.close(); } catch {}
      }
    };
  }, []);

  return (
     <ThemeProvider theme={theme} colorMode="dark">
       <div className="avalon-root">
      <Grid
        templateColumns="1fr 1fr 1fr 1fr"
        templateRows="auto 1fr"   // ⬅️ solo 2 filas: controles + contenido
      >
        {/* ===== Fila 1: controles ===== */}
        <Card columnStart="1" columnEnd="3">
          <Flex direction="row" gap="small" alignItems="center">

            <Button onClick={createNewGame} className="avalon-primary-button">New game</Button>

            {/* Número de jugadores humanos */}
            <Text>Humans:</Text>
            <Input
              type="number"
              className="avalon-number-input"
              min={1}
              max={10}
              width="5rem"
              value={numHumans}
              onChange={(e) => {
                let h = Number(e.target.value);
                if (isNaN(h)) return;
                if (h + numBots > 10) {
                  h = 10 - numBots;
                }
                setNumHumans(h);
              }}
            />

            {/* Número de bots */}
            <Text>Bots:</Text>
            <Input
              type="number"
              className="avalon-number-input"
              min={0}
              max={10}
              width="5rem"
              value={numBots}
              onChange={(e) => {
                let b = Number(e.target.value);
                if (isNaN(b)) return;
                if (b + numHumans > 10) {
                  b = 10 - numHumans;
                }
                setNumBots(b);
              }}
            />
          </Flex>
        </Card>

        <Card columnStart="3" columnEnd="-1" className="avalon-card avalon-controls-card">
          <Flex direction="row" gap="0.75rem" alignItems="center" wrap="wrap">

            {/* Input manual por si alguien quiere escribir el código */}
            <Input
              placeholder="Game Id"
              value={gameIdInput}
              onChange={(e) => setGameIdInput(e.target.value)}
            />

            <Button onClick={() => joinGame()} className="avalon-primary-button">
              Join
            </Button>

            {/* Recargar la lista de partidas activas */}
            <Button onClick={refreshGames} className="avalon-primary-button">
              Refresh games
            </Button>

            {/* Dropdown con las partidas disponibles */}
            <select
              value={gameIdInput}
              onChange={(e) => {
                const id = e.target.value;
                setGameIdInput(id);     // rellena el input
                // si quisieras auto-unirse al seleccionar, podrías hacer: joinGame(id);
              }}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "999px",
                border: "1px solid #444",
                backgroundColor: "#111827",
                color: "white",
                minWidth: "180px",
              }}
            >
              <option value="">Select game…</option>
              {availableGames.map((path, index) => {
                const id = path.split("/").pop(); // "/ws/abc123" -> "abc123"
                const label = `Game ${index + 1}`; // Game 1, Game 2, ...

                return (
                  <option key={path} value={id}>
                    {label}
                  </option>
                );
              })}

            </select>

            {/* Role visible aquí arriba */}
            <Text>Role: {role}</Text>

            {knownEvil.length > 0 && (
              <Text fontSize="0.9rem" style={{ marginLeft: "0.75rem" }}>
                As Merlin you know evil players are:&nbsp;
                {knownEvil
                  .map((idx) => playerNames[idx] || `player-${idx}`)
                  .join(", ")}
              </Text>
            )}

          </Flex>
        </Card>



        {/* ===== Fila 2: contenido izquierda (Viz + renames + QuestBoard) ===== */}
        <Card columnStart="1" columnEnd="3" rowStart="2" rowEnd="-1" className="avalon-card avalon-main-card">

          {/* VizAvalon */}
          <VizAvalon
            history={useDebugViz ? debugHistory : vizHistoryClosed}
            numPlayers={useDebugViz ? 5 : numHumans + numBots}
            playerNames={useDebugViz ? debugPlayerNames : playerNames}
            showVotes={showVotesViz}
            showQuests={showQuestsViz}
          />



          {/* Demo: TeamSelector 
          <div style={{ marginTop: "12px", borderTop: "1px solid #333", paddingTop: "8px" }}>
            <TeamSelector
              playerNames={playerNames}
              numPlayers={numHumans + numBots}
              maxSelected={2}   // cambia este valor para probar distintos tamaños de equipo
              onConfirm={(indices) => {
                console.log("Equipo seleccionado (indices):", indices);
                setDebugSelectedTeam(indices);
              }}
            />

           Texto de debug para que veas que sí está funcionando 
            <Text fontSize="0.8rem" marginTop="0.25rem">
              Debug team: [{debugSelectedTeam.join(", ")}]
            </Text>
          </div>
          */}

          {/* Editor de nombres */}
          <div style={{ marginTop: "8px" }} className="avalon-rename-list">
            {Array.from({ length: numHumans + numBots }, (_, i) => (
              <div
                key={i}
                className="avalon-rename-item"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  fontSize: "0.85rem",
                }}
              >
                <span>{playerNames[i]}</span>
                <Button
                  size="small"
                  variation="link"
                  className="avalon-link-button"
                  onClick={() => {
                    const newName = window.prompt(
                      `Nuevo nombre para player-${i}`,
                      playerNames[i]
                    );
                    if (newName !== null) {
                      handleRenamePlayer(i, newName);
                    }
                  }}
                >
                  Rename
                </Button>
              </div>
            ))}
          </div>

        
        </Card>

        {/* ===== Fila 2: contenido derecha (chat) ===== */}
        <Card columnStart="3" columnEnd="-1" rowStart="2" rowEnd="-1" className="avalon-card avalon-chat-card">

          <div style={{ position: "relative", height: "550px" }}>
            <MainContainer>
              <ChatContainer>
                <MessageList>
                  {messages.map((m, i) => (
                    <MyMessage
                      key={i}
                      message={m.message}
                      playerId={m.index}
                      isNarrator={m.index === -1}
                    />
                  ))}
                  {votingFormIfNeeded()}

                  {isSelectingTeam && (
                    <TeamSelector
                      playerNames={playerNames}
                      numPlayers={totalPlayers}
                      maxSelected={requiredTeamSize}
                      onConfirm={handleTeamConfirm}
                      onCancel={() => setIsSelectingTeam(false)}
                    />
                  )}
                </MessageList>
                <MessageInput
                  placeholder="Type message here"
                  onSend={sendMessage}
                />
              </ChatContainer>
            </MainContainer>
          </div>
        </Card>
      </Grid>
      </div>
    </ThemeProvider>
  );
}