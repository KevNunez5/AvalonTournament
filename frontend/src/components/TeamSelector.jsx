import React, { useMemo, useState } from "react";
import { Button, Text } from "@aws-amplify/ui-react";

/**
 * Props:
 * - playerNames: string[] (nombres visibles, mínimo numPlayers)
 * - numPlayers: number (entre 5 y 10)
 * - maxSelected: number (tamaño del equipo requerido)
 * - onConfirm: (selectedIndices: number[]) => void
 * - onCancel?: () => void   // opcional
 */
function TeamSelector({
  playerNames = [],
  numPlayers = 5,
  maxSelected = 2,
  onConfirm,
  onCancel,
}) {
  const [selected, setSelected] = useState([]); // array de índices (0..numPlayers-1)

  const visiblePlayers = useMemo(
    () => playerNames.slice(0, numPlayers),
    [playerNames, numPlayers]
  );

  const togglePlayer = (index) => {
    setSelected((prev) => {
      // si ya está seleccionado, lo quitamos
      if (prev.includes(index)) {
        return prev.filter((i) => i !== index);
      }
      // si ya alcanzamos el máximo, no dejamos agregar más
      if (prev.length >= maxSelected) {
        return prev;
      }
      return [...prev, index];
    });
  };

  const handleConfirm = () => {
    if (selected.length === 0 || !onConfirm) return;
    onConfirm(selected);
  };

  return (
    <div className="team-selector-root" style={{ padding: "0.75rem" }}>
      <Text as="h3" fontSize="1rem" marginBottom="0.5rem">
        Select {maxSelected} player{maxSelected > 1 ? "s" : ""} for the quest
      </Text>

      <div
        className="team-selector-list"
        style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}
      >
        {visiblePlayers.map((name, index) => {
          const isChecked = selected.includes(index);
          const disableExtra =
            !isChecked && selected.length >= maxSelected;

          return (
            <label
              key={index}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
                opacity: disableExtra ? 0.5 : 1,
                cursor: disableExtra ? "not-allowed" : "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={isChecked}
                disabled={disableExtra}
                onChange={() => togglePlayer(index)}
                style={{ transform: "scale(1.1)" }}
              />
              <span style={{ fontSize: "0.9rem", color: "white" }}>{name}</span>
            </label>
          );
        })}
      </div>

      <div
        className="team-selector-actions"
        style={{
          display: "flex",
          justifyContent: onCancel ? "space-between" : "flex-end",
          gap: "0.5rem",
          marginTop: "0.75rem",
        }}
      >
        {onCancel && (
          <Button size="small" variation="link" onClick={onCancel}>
            Cancel
          </Button>
        )}

        <Button
          size="small"
          className="avalon-primary-button"
          isDisabled={selected.length !== maxSelected}
          onClick={handleConfirm}
        >
          Accept ({selected.length}/{maxSelected})
        </Button>
      </div>
    </div>
  );
}

export default TeamSelector;
