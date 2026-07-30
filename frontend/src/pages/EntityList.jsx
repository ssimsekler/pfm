// Config-driven CRUD list report → reusable EntityManager (MUI).
// Loans and installment plans get a "schedule" row action to open the
// payment-tracking dialog (#15/#16).
import { useState } from "react";
import { Typography } from "@mui/material";
import EventNoteIcon from "@mui/icons-material/EventNote";
import EntityManager from "../components/EntityManager";
import ScheduleDialog from "../components/ScheduleDialog";
import { ENTITIES } from "../entities";

const SCHEDULE_KIND = {
  loans: "loan",
  "installment-plans": "installment",
};

export default function EntityList({ entity }) {
  const cfg = ENTITIES[entity];
  const [scheduleRow, setScheduleRow] = useState(null);
  if (!cfg) {
    return <Typography>Unknown entity: {entity}</Typography>;
  }

  const kind = SCHEDULE_KIND[entity];
  const rowActions = kind
    ? [
        {
          icon: <EventNoteIcon fontSize="small" />,
          tooltip: "Schedule & payments",
          onClick: (row) => setScheduleRow(row),
        },
      ]
    : undefined;

  return (
    <>
      <EntityManager entity={entity} cfg={cfg} rowActions={rowActions} />
      {scheduleRow ? (
        <ScheduleDialog record={scheduleRow} kind={kind} onClose={() => setScheduleRow(null)} />
      ) : null}
    </>
  );
}