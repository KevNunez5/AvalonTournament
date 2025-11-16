// frontend/src/components/QuestBoard.jsx
import React from "react";

/**
 * QuestBoard (WIP/skeleton)
 * Props (aún no usadas, pero definidas para el wiring posterior):
 *  - numPlayers?: number (default 5)
 *  - questSetup?: number[]  // jugadores requeridos por misión (default 5p: [2,3,2,3,3])
 *  - history?: any[]        // la conectaremos después
 *  - width?: number
 *  - height?: number
 */
export default function QuestBoard({
  numPlayers = 5,
  questSetup = [2, 3, 2, 3, 3],
  history = [],
  width = 420,
  height = 220,
}) {
  // --- Layout base (solo placeholders) ---
  const padX = 24;
  const padY = 20;

  // Quest Track (5 misiones)
  const questCount = 5;
  const questSpacing = (width - padX * 2) / (questCount - 1);
  const questY = padY + 40; // fila superior

  // Vote Track (5 intentos)
  const voteCount = 5;
  const voteSpacing = (width - padX * 2) / (voteCount - 1);
  const voteY = height - padY - 30; // fila inferior

  return (
    <svg width={width} height={height}>
      {/* Títulos (placeholders) */}
      <text x={padX} y={20} fontSize="14" fontWeight="600" fill="#111827">
        Quest Board (WIP)
      </text>

      {/* === QUEST TRACK (placeholder) === */}
      <g>
        <text x={padX} y={questY - 20} fontSize="12" fill="#374151">
          Quests
        </text>
        {Array.from({ length: questCount }, (_, i) => {
          const cx = padX + i * questSpacing;
          return (
            <g key={`q-${i}`}>
              {/* círculo de misión (gris claro por ahora) */}
              <circle cx={cx} cy={questY} r={18} fill="#e5e7eb" stroke="#9ca3af" />
              {/* número de jugadores requeridos (del questSetup) */}
              <text
                x={cx}
                y={questY + 4}
                textAnchor="middle"
                fontSize="12"
                fill="#111827"
              >
                {questSetup[i] ?? "?"}
              </text>
              {/* etiqueta Quest i+1 */}
              <text
                x={cx}
                y={questY + 36}
                textAnchor="middle"
                fontSize="11"
                fill="#6b7280"
              >
                Q{i + 1}
              </text>
            </g>
          );
        })}
      </g>

      {/* === VOTE TRACK (placeholder) === */}
      <g>
        <text x={padX} y={voteY - 24} fontSize="12" fill="#374151">
          Vote track
        </text>
        {Array.from({ length: voteCount }, (_, i) => {
          const cx = padX + i * voteSpacing;
          return (
            <g key={`v-${i}`}>
              <circle cx={cx} cy={voteY} r={10} fill="#f3f4f6" stroke="#9ca3af" />
              <text
                x={cx}
                y={voteY + 4}
                textAnchor="middle"
                fontSize="10"
                fill="#6b7280"
              >
                {i + 1}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
