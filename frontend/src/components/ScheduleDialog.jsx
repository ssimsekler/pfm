// Installment / loan schedule + payment tracking dialog (#15/#16).
// Works for both entities via `kind`:
//   kind="installment" → /v1/installment-plans/{id}/schedule  (rows: seq/due_date/amount)
//   kind="loan"        → /v1/loans/{id}/schedule              (rows: period/due_date/principal_portion/interest_portion/balance)
// "Generate" builds the schedule; "Pay" records a linked transaction on a row.
import { useCallback, useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, Alert, Typography, Tooltip, Box,
} from "@mui/material";
import PaidIcon from "@mui/icons-material/Paid";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { api } from "../api";
import ComboField from "./ComboField";

const ACCOUNT_FIELD = { type: "ref", refEntity: "accounts" };

export default function ScheduleDialog({ record, kind, onClose }) {
  const isLoan = kind === "loan";
  const base = isLoan ? "/v1/loans" : "/v1/installment-plans";
  const [rows, setRows] = useState([]);
  const [accountId, setAccountId] = useState(record.account_id || "");
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const r = await api.get(`${base}/${record.uuid}/schedule`).catch(() => []);
    setRows(r || []);
  }, [base, record.uuid]);

  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post(`${base}/${record.uuid}/generate`, {});
      setMsg("Schedule generated.");
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const pay = async (row) => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post(`${base}/${record.uuid}/schedule/${row.uuid}/pay`,
        accountId ? { account_id: accountId } : {});
      setMsg("Payment recorded.");
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{isLoan ? "Loan schedule" : "Installment schedule"} — {record.name}</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}

        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
          <Box sx={{ minWidth: 240 }}>
            <ComboField field={ACCOUNT_FIELD} value={accountId} onChange={setAccountId} label="Pay from account" />
          </Box>
          <Button startIcon={<PlaylistAddIcon />} onClick={generate} disabled={busy}>
            Generate schedule
          </Button>
        </Stack>

        <Table size="small">
          <TableHead>
            {isLoan ? (
              <TableRow>
                <TableCell>#</TableCell><TableCell>Due</TableCell>
                <TableCell align="right">Principal</TableCell><TableCell align="right">Interest</TableCell>
                <TableCell align="right">Balance</TableCell><TableCell>Paid</TableCell><TableCell />
              </TableRow>
            ) : (
              <TableRow>
                <TableCell>#</TableCell><TableCell>Due</TableCell>
                <TableCell align="right">Amount</TableCell><TableCell>Paid</TableCell><TableCell />
              </TableRow>
            )}
          </TableHead>
          <TableBody>
            {rows.map((r) => {
              const paid = Boolean(r.linked_txn_id);
              return (
                <TableRow key={r.uuid} hover>
                  <TableCell>{isLoan ? r.period : r.seq}</TableCell>
                  <TableCell>{r.due_date}</TableCell>
                  {isLoan ? (
                    <>
                      <TableCell align="right">{r.principal_portion}</TableCell>
                      <TableCell align="right">{r.interest_portion}</TableCell>
                      <TableCell align="right">{r.balance}</TableCell>
                    </>
                  ) : (
                    <TableCell align="right">{r.amount}</TableCell>
                  )}
                  <TableCell>{paid ? <CheckCircleIcon fontSize="small" color="success" /> : ""}</TableCell>
                  <TableCell align="right">
                    <Tooltip title={paid ? "Already paid" : "Record payment"}>
                      <span>
                        <IconButton size="small" color="primary" disabled={busy || paid} onClick={() => pay(r)}>
                          <PaidIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              );
            })}
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={isLoan ? 7 : 5}>
                <Typography color="text.secondary">No schedule yet — click “Generate schedule”.</Typography>
              </TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}