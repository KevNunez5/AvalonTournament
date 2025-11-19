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

const STAGE = {
  REVEAL: "RevealingRoles",
  SELECT_TEAM: "SelectingTeam",
  VOTE_TEAM: "VotingTeam",
  VOTE_QUEST: "VotingQuest",
  TEAM_VOTED: "TeamVoted",
  QUEST_VOTED: "QuestVoted",
};

const theme = { name: "my-theme", overrides: [defaultDarkModeOverride] };

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

  // ===== Helpers para parsing de mensajes a "history" (Viz-ready) =====
  const history = useMemo(() => {
    // Construye intentos/rondas a partir de los textos que emite el server/bots
    const rounds = [];
    let holder = null;

    const pushHolder = () => {
      if (holder) {
        rounds.push(holder);
        holder = null;
      }
    };

    for (const m of messages) {
      const text = m.message;

      // Propuesta de equipo
      // "Player i proposes the following team [a,b]"
      const prop = text?.match(/^Player (\d+) proposes the following team \[([0-9, ]*)\]/);
      if (prop) {
        const leader = `player-${prop[1]}`;
        const team = prop[2]
          .split(",")
          .filter(Boolean)
          .map((s) => `player-${Number(s.trim())}`);
        holder = { leader, team, votes: [] };
        continue;
      }

      // Votos al equipo
      // "Player j voted 'True' on team"
      const vteam = text?.match(/^Player (\d+) voted '(\w+)' on team/);
      if (vteam && holder) {
        const player = `player-${vteam[1]}`;
        const v = vteam[2].toLowerCase() === "true" ? "yes" : "no";
        holder.votes = [...(holder.votes || []).filter((x) => x.player !== player), { player, vote: v }];
        continue;
      }

      // Resultado de equipo aceptado
      if (text === "Team accepted!" && holder) {
        holder.team_vote_outcome = "succeeded";
        // no push aún, esperamos "Quest result"
        continue;
      }

      // Resultado de misión
      // "Quest result True/False"
      const q = text?.match(/^Quest result (True|False)/);
      if (q && holder) {
        holder.quest_vote_outcome = q[1] === "True" ? "succeeded" : "failed";
        pushHolder();
        continue;
      }

      // Inferir equipo rechazado cuando vuelve "Asked Player X to select a team"
      if (text?.startsWith("Asked Player") && text?.includes("to select a team")) {
        if (holder && !holder.team_vote_outcome) {
          holder.team_vote_outcome = "failed";
          pushHolder();
        }
      }
    }

    return rounds;
  }, [messages]);

  const wrapperSetVote = (value) => setVote(value);

  // ====== Crear juego (observador) ======
  const createNewGame = async () => {
    // Si ya hay socket, ciérralo
    if (wspRef.current) {
      try { await wspRef.current.close(); } catch {}
      wspRef.current = null;
    }

    const resp = await fetch("http://localhost:8888/games", { method: "POST" });
    // abrir WS como observador
    const wsp = new WebSocketAsPromised("ws://localhost:8888/ws");
    await wsp.open();
    wspRef.current = wsp;
    wsp.onMessage.addListener((data) => {
      const msg = JSON.parse(data);
      // Normalizamos siempre a {message, index, action?}
      setMessages((prev) => [...prev, { message: msg.message, index: msg.index, action: msg.action }]);
    });
  };

  // ====== Unirse como jugador ======
  const joinGame = async () => {
    if (wspRef.current) {
      try { await wspRef.current.close(); } catch {}
      wspRef.current = null;
    }
    const wsp = new WebSocketAsPromised("ws://localhost:8888/ws");
    await wsp.open();
    wspRef.current = wsp;

    wsp.onMessage.addListener((data) => {
      const msg = JSON.parse(data);

      if (msg.action === "RevealRoles") {
        gameState.current = {
          index: msg.index,
          role: msg.roles[msg.index],
          stage: STAGE.REVEAL,
        };
        setRole(gameState.current.role);
        setMessages((prev) => [
          ...prev,
          { message: `I am Player ${gameState.current.index}, with role '${gameState.current.role}'`, index: -1 }
        ]);
        return;
      }
      if (msg.action === "VoteTeam") {
        gameState.current.stage = STAGE.VOTE_TEAM;
        setVote(null);
      } else if (msg.action === "VoteQuest") {
        gameState.current.stage = STAGE.VOTE_QUEST;
        setVote(null);
      } else if (msg.action === "SelectTeam") {
        gameState.current.stage = STAGE.SELECT_TEAM;
      }

      setMessages((prev) => [...prev, { message: msg.message, index: msg.index, action: msg.action }]);
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

  useEffect(() => {
    return () => {
      if (wspRef.current) {
        try { wspRef.current.close(); } catch {}
      }
    };
  }, []);

  return (
    <ThemeProvider>
      {/* theme={theme} colorMode="dark"> */}
      <Grid
        templateColumns="1fr 1fr 1fr 1fr"
        templateRows="auto 1fr"   // ⬅️ solo 2 filas: controles + contenido
      >
        {/* ===== Fila 1: controles ===== */}
        <Card columnStart="1" columnEnd="3">
          <Flex direction="row" gap="small" alignItems="center">
            <Button onClick={createNewGame}>New game</Button>

            {/* Número de jugadores humanos */}
            <Text>Humans:</Text>
            <Input
              type="number"
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

        <Card columnStart="3" columnEnd="-1">
          <Flex direction="row" gap="small" alignItems="center">
            <Input placeholder="Game Id" />
            <Button onClick={joinGame}>Join</Button>

            {/* Role visible aquí arriba */}
            <Text>Role: {role}</Text>

            {/* Checkbox: mostrar/ocultar matriz de votos */}
            <label style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <input
                type="checkbox"
                checked={showVotesViz}
                onChange={(e) => setShowVotesViz(e.target.checked)}
                style={{ transform: "scale(1.1)" }}   // opcional, solo para que se vea más grande
              />
              <Text fontSize="0.9rem">Show votes grid</Text>
            </label>

            {/* Checkbox: mostrar/ocultar panel de quests */}
            <label style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <input
                type="checkbox"
                checked={showQuestsViz}
                onChange={(e) => setShowQuestsViz(e.target.checked)}
                style={{ transform: "scale(1.1)" }}
              />
              <Text fontSize="0.9rem">Show quests panel</Text>
            </label>

          </Flex>
        </Card>


        {/* ===== Fila 2: contenido izquierda (Viz + renames + QuestBoard) ===== */}
        <Card columnStart="1" columnEnd="3" rowStart="2" rowEnd="-1">
          {/* VizAvalon */}
          <VizAvalon
            history={history}
            numPlayers={numHumans + numBots}
            playerNames={playerNames}
            showVotes={showVotesViz}
            showQuests={showQuestsViz}
          />

          {/* Editor de nombres */}
          <div style={{ marginTop: "8px" }}>
            {Array.from({ length: numHumans + numBots }, (_, i) => (
              <div
                key={i}
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

          {/* QuestBoard debajo de la visualización */}
          {showAnalytics && (
            <div style={{ marginTop: "24px" }}>
              <QuestBoard
                numPlayers={5}
                questSetup={[2, 3, 2, 3, 3]}
                // en el siguiente paso: history={history}
              />
            </div>
          )}
        </Card>

        {/* ===== Fila 2: contenido derecha (chat) ===== */}
        <Card columnStart="3" columnEnd="-1" rowStart="2" rowEnd="-1">
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
    </ThemeProvider>
  );
}