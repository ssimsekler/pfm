// Transactions page: full CRUD via the reusable EntityManager, including
// multi-line split editing (SplitEditor) and Policy 1 handling. A "New Transfer"
// action opens the dual-leg transfer dialog (A.5).
import { useState } from "react";
import { Button, Snackbar, Alert } from "@mui/material";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import EntityManager from "../components/EntityManager";
import TransferDialog from "../components/TransferDialog";
import { ENTITIES } from "../entities";

export default function Transactions() {
  const [transferOpen, setTransferOpen] = useState(false);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [msg, setMsg] = useState(null);

  const extra = (
    <Button variant="outlined" startIcon={<SwapHorizIcon />} onClick={() => setTransferOpen(true)}>
      New Transfer
    </Button>
  );

  return (
    <>
      <EntityManager
        entity="transactions"
        cfg={ENTITIES.transactions}
        extra={extra}
        refreshSignal={refreshSignal}
      />
      {transferOpen ? (
        <TransferDialog
          onClose={() => setTransferOpen(false)}
          onDone={() => {
            setTransferOpen(false);
            setMsg("Transfer created (two linked transactions).");
            setRefreshSignal((s) => s + 1);
          }}
        />
      ) : null}
      <Snackbar open={Boolean(msg)} autoHideDuration={5000} onClose={() => setMsg(null)}>
        <Alert severity="success" onClose={() => setMsg(null)}>{msg}</Alert>
      </Snackbar>
    </>
  );
}