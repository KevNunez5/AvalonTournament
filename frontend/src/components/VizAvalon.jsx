// frontend/src/components/VizAvalon.jsx
import React, { useMemo } from "react";

/**
 * Props esperadas:
 * - history: [
 *    {
 *      leader: "player-0",
 *      team: ["player-0", "player-1"],
 *      votes: [{ player: "player-0", vote: "yes" | "no" }, ...],
 *      team_vote_outcome: "succeeded" | "failed",
 *      quest_vote_outcome: "succeeded" | "failed"
 *    },
 *   ...
 * ]
 * - numPlayers: número de jugadores (default 5)
 * - width, rowHeight: opcionales para tunear layout
 */
export default function VizAvalon({
  history = [],
  numPlayers = 5,
  width = 600,
  rowHeight = 28,
  showVotes = true,
  showQuests = true
}) {

  // Construye la lista de players: player-0 ... player-(n-1)
  const players = useMemo(
    () => Array.from({ length: numPlayers }, (_, i) => `player-${i}`),
    [numPlayers]
  );

  const getColor = (result) =>
    result === "succeeded" ? "green" : result === "failed" ? "red" : "lightgray";

  // Dimensiones y offsets
  const leftLabelX = 50;
  const leftTopY = 15;
  const colXStart = 180;
  const voteRectSize = 20;

  // Segunda lista de nombres (parte baja)
  const lowerLabelsYStart = 200;

  // Caja vertical que marca el bloque del equipo en cada ronda (en la lista inferior)
  const teamBlockYOffset = 182;
  const leaderMarkYOffset = 186;
  const memberDotYCenterOffset = 194;

  // Anchos
  const teamBlockWidth = 23;
  const colStep = 50;

  return (
    <svg width={width} height={Math.max(360, lowerLabelsYStart + numPlayers * rowHeight)}>
      {/* Nombres (arriba) */}
      {players.map((name, idx) => (
        <text key={`name-top-${name}`} x={leftLabelX} y={leftTopY + idx * rowHeight} fill="black">
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

                {/* Hacer que las votacions tengan simbolos de Y/N
                <text
                  x={x + voteRectSize / 2}
                  y={y + voteRectSize / 2 + 4}
                  textAnchor="middle"
                  fontSize="10"
                  fill="white"
                >
                  {isYes ? "Y" : "N"}
                </text>

                */}

              </g>
            );
          })
        )}


      {/* Nombres (abajo) */}
      {players.map((name, idx) => (
        <text key={`name-bottom-${name}`} x={leftLabelX} y={lowerLabelsYStart + idx * rowHeight} fill="black">
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
                  {/* Rectángulo coloreado por resultado de misión: ocupa TODAS las filas */}
                  <rect
                    x={colXStart - 12 + roundIdx * colStep}
                    y={teamBlockYOffset + 0 * rowHeight}
                    width={teamBlockWidth}
                    height={numPlayers * rowHeight - 4}
                    rx="1%"
                    fill={getColor(round.quest_vote_outcome)}
                    fillOpacity="0.4"
                  />
                  {/* Línea si el equipo fue RECHAZADO: también toda la columna */}
                  {round.team_vote_outcome === "failed" ? (
                    <line
                      x1={colXStart + roundIdx * colStep}
                      y1={teamBlockYOffset + 0 * rowHeight}
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
