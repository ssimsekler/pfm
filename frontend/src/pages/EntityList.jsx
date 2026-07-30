// Config-driven CRUD list report → reusable EntityManager (MUI).
// Loans and installment plans get a "schedule" row action to open the
// payment-tracking dialog (#15/#16).
import { useState } from "react";
import { Typography } from "@mui/material";
import EventNoteIcon from "@mui/icons-material/EventNote";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import EntityManager from "../components/EntityManager";
import ScheduleDialog from "../components/ScheduleDialog";
import ValuationDialog from "../components/ValuationDialog";
import { ENTITIES } from "../entities";

const SCHEDULE_KIND = {
  loans: "loan",
  "installment-plans": "installment",
};

export default function EntityList({ entity }) {
  const cfg = ENTITIES[entity];
  const [scheduleRow, setScheduleRow] = useState(null);
  const [valuationRow, setValuationRow] = useState(null);
  if (!cfg) {
    return <Typography>Unknown entity: {entity}</Typography>;
  }

  const kind = SCHEDULE_KIND[entity];
  let rowActions;
  if (kind) {
    rowActions = [
      {
        icon: <EventNoteIcon fontSize="small" />,
        tooltip: "Schedule & payments",
        onClick: (row) => setScheduleRow(row),
      },
    ];
  } else if (entity === "investments") {
    rowActions = [
      {
        icon: <ShowChartIcon fontSize="small" />,
        tooltip: "Valuation history",
        onClick: (row) => setValuationRow(row),
      },
    ];
  }

  return (
    <>
      <EntityManager entity={entity} cfg={cfg} rowActions={rowActions} />
      {scheduleRow ? (
        <ScheduleDialog record={scheduleRow} kind={kind} onClose={() => setScheduleRow(null)} />
      ) : null}
      {valuationRow ? (
        <ValuationDialog record={valuationRow} onClose={() => setValuationRow(null)} />
      ) : null}
    </>
  );
}
