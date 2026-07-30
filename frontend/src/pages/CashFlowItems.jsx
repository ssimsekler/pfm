// Cash Flow Items page: standard CRUD + a per-row "Create transaction" action
// that materializes a transaction linked to the item (inherits its category,
// no split — Policy 1). Keeps the transaction form free of the cash-flow-item
// field per the agreed flow.
import { useState } from "react";
import { Snackbar, Alert } from "@mui/material";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import EntityManager from "../components/EntityManager";
import MaterializeDialog from "../components/MaterializeDialog";
import { ENTITIES } from "../entities";

export default function CashFlowItems() {
  const [item, setItem] = useState(null);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [msg, setMsg] = useState(null);

  const rowActions = [
    {
      tooltip: "Create transaction from this item",
      color: "primary",
      icon: <ReceiptLongIcon fontSize="small" />,
      onClick: (row) => setItem(row),
    },
  ];

  return (
    <>
      <EntityManager
        entity="cash-flow-items"
        cfg={ENTITIES["cash-flow-items"]}
        rowActions={rowActions}
        refreshSignal={refreshSignal}
      />
      {item ? (
        <MaterializeDialog
          item={item}
          onClose={() => setItem(null)}
          onDone={() => { setItem(null); setMsg("Transaction created from cash flow item."); setRefreshSignal((s) => s + 1); }}
        />
      ) : null}
      <Snackbar open={Boolean(msg)} autoHideDuration={5000} onClose={() => setMsg(null)}>
        <Alert severity="success" onClose={() => setMsg(null)}>{msg}</Alert>
      </Snackbar>
    </>
  );
}