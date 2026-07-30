// Budgets page: CRUD + per-row "Manage lines" action (#6).
import { useState } from "react";
import ListAltIcon from "@mui/icons-material/ListAlt";
import EntityManager from "../components/EntityManager";
import BudgetLinesDialog from "../components/BudgetLinesDialog";
import { ENTITIES } from "../entities";

export default function Budgets() {
  const [budget, setBudget] = useState(null);

  const rowActions = [
    {
      tooltip: "Manage budget lines",
      color: "primary",
      icon: <ListAltIcon fontSize="small" />,
      onClick: (row) => setBudget(row),
    },
  ];

  return (
    <>
      <EntityManager entity="budgets" cfg={ENTITIES.budgets} rowActions={rowActions} />
      {budget ? <BudgetLinesDialog budget={budget} onClose={() => setBudget(null)} /> : null}
    </>
  );
}