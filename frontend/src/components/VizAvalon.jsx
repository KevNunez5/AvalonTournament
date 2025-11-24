// frontend/src/components/VizAvalon.jsx
import React, { useMemo } from "react";

/**
 * Props esperadas:
 * - history: [...]
 * - numPlayers: número de jugadores (default 5)
 * - width, rowHeight: opcionales
 * - showVotes, showQuests: toggles de secciones
 * - playerNames: nombres visibles (array de length >= numPlayers)
 */

export default function VizAvalon({
  history = [],
  numPlayers = 5,
  width = 600,
  rowHeight = 28,
  showVotes = true,
  showQuests = true,
  playerNames,
}) {
  // IDs internos: player-0 ... player-(n-1)
  const players = useMemo(
    () => Array.from({ length: numPlayers }, (_, i) => `player-${i}`),
    [numPlayers]
  );

  // ⭐ NOMBRES VISIBLES: si hay playerNames se usan, si no, usamos los IDs
  const labels = useMemo(
    () =>
      playerNames && playerNames.length >= numPlayers
        ? playerNames.slice(0, numPlayers)
        : players,
    [playerNames, players, numPlayers]
  );

  // ===== LOGS DE DEBUG =====
  console.log("[VizAvalon] render");
  console.log("[VizAvalon] numPlayers =", numPlayers);
  console.log("[VizAvalon] labels =", labels);
  console.log("[VizAvalon] history =", history);

  const getColor = (result) =>
    result === "succeeded" ? "GreenYellow" : result === "failed" ? "#F53020" : "lightgray";

  // Dimensiones y offsets
  const leftLabelX = 50;
  const leftTopY = 15;
  const colXStart = 180;
  const voteRectSize = 20;

  // Altura que ocupa la lista de nombres de arriba
  const topNamesBottomY = leftTopY + numPlayers * rowHeight;

  // Espacio entre la sección de arriba y la de abajo
  const gapBetweenSections = 45;

  // Segunda lista de nombres (parte baja), justo debajo de la de arriba
  const lowerLabelsYStart = topNamesBottomY + gapBetweenSections;

  // Offsets de la parte de quests, relativos a lowerLabelsYStart
  const teamBlockYOffset       = lowerLabelsYStart - 18;
  const leaderMarkYOffset      = lowerLabelsYStart - 14;
  const memberDotYCenterOffset = lowerLabelsYStart - 6;

  // Anchos
  const teamBlockWidth = 23;
  const colStep = 50;

  return (
    <svg
      width={width}
      height={Math.max(360, lowerLabelsYStart + numPlayers * rowHeight)}

    >
      {/* ⭐ Nombres (arriba) usando labels */}
      {labels.map((name, idx) => (
        <text
          key={`name-top-${players[idx]}`}
          x={leftLabelX}
          y={leftTopY + idx * rowHeight}
          fill="#f1f5f9"
        >
          {name}
        </text>
      ))}

      {/* Matriz de votos por ronda (arriba-derecha) */}
      {showVotes &&
        history.map((round, roundIdx) =>
          (round.votes || []).map((vote, vIdx) => {
            const raw = vote?.vote;
            const normalized = String(raw).trim().toLowerCase();
            const isYes =
              raw === true || raw === 1 || /^(true|yes|y|1)$/i.test(normalized);

            const x = colXStart - 12 + roundIdx * colStep;
            const playerRow = players.indexOf(vote?.player);
            if (playerRow === -1) return null;
            const y = 1 + playerRow * rowHeight;

            return (
              <g key={`vote-${roundIdx}-${vIdx}`}>
                <rect
                  x={x}
                  y={y}
                  height={voteRectSize}
                  width={voteRectSize}
                  fill={isYes ? "gray" : "orange"}
                >
                  <title>{`player: ${vote?.player} | raw: ${String(raw)}`}</title>
                </rect>
              </g>
            );
          })
        )}

      {/* ⭐ Nombres (abajo) usando labels */}
      {labels.map((name, idx) => (
        <text
          key={`name-bottom-${players[idx]}`}
          x={leftLabelX}
          y={lowerLabelsYStart + idx * rowHeight}
          fill="#f1f5f9"
        >
          {name}
        </text>
      ))}

      {showQuests && (
        <>
          {/* Bloque de equipo y línea de rechazo/aceptado por ronda */}
          <g>
            {history.map((round, roundIdx) => {
              const teamIdxs = (round.team || [])
                .map((p) => players.indexOf(p))
                .filter((i) => i >= 0);
              if (teamIdxs.length === 0) return null;

              return (
                <g key={`team-block-${roundIdx}`}>
                  <rect
                    x={colXStart - 12 + roundIdx * colStep}
                    y={teamBlockYOffset}
                    width={teamBlockWidth}
                    height={numPlayers * rowHeight - 4}
                    rx="1%"
                    fill={getColor(round.quest_vote_outcome)}
                    fillOpacity="0.5"
                  />
                  {round.team_vote_outcome === "failed" ? (
                    <line
                      x1={colXStart + roundIdx * colStep}
                      y1={teamBlockYOffset}
                      x2={colXStart + roundIdx * colStep}
                      y2={teamBlockYOffset - 2 + numPlayers * rowHeight}
                      stroke="gray"
                      strokeWidth={5}
                    />
                  ) : null}
                </g>
              );
            })}
          </g>

          {/* Marcadores de líder y miembros por ronda (en la lista inferior) */}
          <g>
            {history.flatMap((round, roundIdx) =>
              players.map((p, pIdx) => {
                const isLeader = round.leader === p;
                const inTeam = (round.team || []).includes(p);

                if (isLeader) {
                  return inTeam ? (
                    <rect
                      key={`lead-in-${roundIdx}-${p}`}
                      x={colXStart - 8 + roundIdx * colStep}
                      y={leaderMarkYOffset + pIdx * rowHeight}
                      width={16}
                      height={16}
                      fill="black"
                    />
                  ) : (
                    <rect
                      key={`lead-out-${roundIdx}-${p}`}
                      x={colXStart - 8 + roundIdx * colStep}
                      y={leaderMarkYOffset + pIdx * rowHeight}
                      width={16}
                      height={16}
                      stroke="black"
                      fill="gray"
                    />
                  );
                } else {
                  return inTeam ? (
                    <circle
                      key={`member-in-${roundIdx}-${p}`}
                      cx={colXStart + roundIdx * colStep}
                      cy={memberDotYCenterOffset + pIdx * rowHeight}
                      r={8}
                      fill="black"
                    />
                  ) : (
                    <circle
                      key={`member-out-${roundIdx}-${p}`}
                      cx={colXStart + roundIdx * colStep}
                      cy={memberDotYCenterOffset + pIdx * rowHeight}
                      r={8}
                      fill="none"
                      stroke="gray"
                    />
                  );
                }
              })
            )}
          </g>
        </>
      )}
    </svg>
  );
}
