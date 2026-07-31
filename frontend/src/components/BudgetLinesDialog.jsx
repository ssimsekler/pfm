// Budget lines editor (#6, Session 742 #12/#22): manage lines under a budget and
// show variance. A line is EITHER driven by a Cash Flow Item (its category +
// direction are inherited and the category/direction inputs are hidden) OR a
// Category + Direction pair. The table resolves Category/CFI/Direction UUIDs to
// human labels (#22).
// Backend: GET/POST/DELETE /v1/budgets/{id}/lines, GET /v1/budgets/{id}/variance.
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, TextField, Alert, Box, Typography, Divider,
  ToggleButton, ToggleButtonGroup,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import AssessmentIcon from "@mui/icons-material/Assessment";
import { api } from "../api";
import ComboField from "./ComboField";
import ConfirmDialog from "./ConfirmDialog";

const CATEGORY_FIELD = { type: "ref", refEntity: "expense-categories" };
const CFI_FIELD = { type: "ref", refEntity: "cash-flow-items" };
const DIRECTION_FIELD = { type: "codeValue", listKey: "txn_direction" };

// Load an id→label map for a ref entity (by uuid) or a code list (by uuid).
async function loadLabelMap({ path, listKey }) {
  const map = {};
  try {
    if (listKey) {
      const rows = await api.get(`/v1/code-lists/${listKey}/values`);
      (rows || []).forEach((r) => { map[r.uuid] = r.label || r.code; });
    } else if (path) {
      const data = await api.get(path, { limit: 500 });
      const items = Array.isArray(data) ? data : data.items || [];
      items.forEach((r) => { map[r.uuid] = r.name || r.mnemonic_id || r.uuid; });
    }
  } catch { /* ignore */ }
  return map;
}

export default function BudgetLinesDialog({ budget, onClose }) {
  const [lines, setLines] = useState([]);
  const [mode, setMode] = useState("item"); // "item" | "category"
  const [draft, setDraft] = useState({ expense_category_id: "", cash_flow_item_id: "", direction_cv_id: "", expected_amount: "" });
  const [variance, setVariance] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [deleteId, setDeleteId] = useState(null);

  // Label maps for #22 (resolve UUIDs → text).
  const [catMap, setCatMap] = useState({});
  const [cfiMap, setCfiMap] = useState({});
  const [dirMap, setDirMap] = useState({});

  const load = useCallback(async () => {
    const rows = await api.get(`/v1/budgets/${budget.uuid}/lines`).catch(() => []);
    setLines(rows || []);
  }, [budget.uuid]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    loadLabelMap({ path: "/v1/expense-categories" }).then(setCatMap);
    loadLabelMap({ path: "/v1/cash-flow-items" }).then(setCfiMap);
    loadLabelMap({ listKey: "txn_direction" }).then(setDirMap);
  }, []);

  const addLine = async () => {
    if (!draft.expected_amount) { setError("Enter an expected amount."); return; }
    if (mode === "item" && !draft.cash_flow_item_id) { setError("Select a cash flow item."); return; }
    if (mode === "category" && (!draft.expense_category_id || !draft.direction_cv_id)) {
      setError("Select both a category and a direction."); return;
    }
    setBusy(true); setError(null);
    try {
      const body = mode === "item"
        ? { cash_flow_item_id: draft.cash_flow_item_id, expected_amount: Number(draft.expected_amount) }
        : {
            expense_category_id: draft.expense_category_id,
            direction_cv_id: draft.direction_cv_id,
            expected_amount: Number(draft.expected_amount),
          };
      await api.post(`/v1/budgets/${budget.uuid}/lines`, body);
      setDraft({ expense_category_id: "", cash_flow_item_id: "", direction_cv_id: "", expected_amount: "" });
      load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doDelete = async () => {
    setBusy(true); setError(null);
    try {
      await api.del(`/v1/budgets/${budget.uuid}/lines/${deleteId}`);
      setDeleteId(null);
      load();
    } catch (e) { setDeleteId(null); setError(e.message); } finally { setBusy(false); }
  };

  const loadVariance = async () => {
    setError(null);
    const v = await api.get(`/v1/budgets/${budget.uuid}/variance`).catch((e) => { setError(e.message); return null; });
    setVariance(v);
  };

  const label = (map, id) => (id ? (map[id] || id) : "");

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Budget lines — {budget.name}</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Category</TableCell><TableCell>Cash Flow Item</TableCell>
              <TableCell>Direction</TableCell><TableCell align="right">Expected</TableCell><TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {lines.map((l) => (
              <TableRow key={l.uuid} hover>
                <TableCell>{label(catMap, l.expense_category_id)}</TableCell>
                <TableCell>{label(cfiMap, l.cash_flow_item_id)}</TableCell>
                <TableCell>{label(dirMap, l.direction_cv_id)}</TableCell>
                <TableCell align="right">{l.expected_amount}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" color="error" onClick={() => setDeleteId(l.uuid)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {lines.length === 0 ? <TableRow><TableCell colSpan={5}><Typography color="text.secondary">No lines yet.</Typography></TableCell></TableRow> : null}
          </TableBody>
        </Table>

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Add a line</Typography>
        <ToggleButtonGroup
          size="small" exclusive value={mode}
          onChange={(_e, v) => { if (v) { setMode(v); setError(null); } }}
          sx={{ mb: 1.5 }}
        >
          <ToggleButton value="item">By Cash Flow Item</ToggleButton>
          <ToggleButton value="category">By Category + Direction</ToggleButton>
        </ToggleButtonGroup>

        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexWrap: "wrap" }}>
          {mode === "item" ? (
            <Box sx={{ minWidth: 240 }}>
              <ComboField field={CFI_FIELD} value={draft.cash_flow_item_id}
                onChange={(v) => setDraft({ ...draft, cash_flow_item_id: v })} label="Cash Flow Item" />
              <Typography variant="caption" color="text.secondary">
                Category &amp; direction are inherited from the item.
              </Typography>
            </Box>
          ) : (
            <>
              <Box sx={{ minWidth: 200 }}>
                <ComboField field={CATEGORY_FIELD} value={draft.expense_category_id}
                  onChange={(v) => setDraft({ ...draft, expense_category_id: v })} label="Category" />
              </Box>
              <Box sx={{ minWidth: 150 }}>
                <ComboField field={DIRECTION_FIELD} value={draft.direction_cv_id}
                  onChange={(v) => setDraft({ ...draft, direction_cv_id: v })} label="Direction" />
              </Box>
            </>
          )}
          <TextField label="Expected" type="number" size="small" value={draft.expected_amount}
            onChange={(e) => setDraft({ ...draft, expected_amount: e.target.value })} sx={{ width: 130 }} />
          <Button variant="contained" startIcon={<AddIcon />} onClick={addLine} disabled={busy}>Add</Button>
        </Stack>

        <Divider sx={{ my: 2 }} />
        <Stack direction="row" spacing={2} alignItems="center">
          <Button startIcon={<AssessmentIcon />} onClick={loadVariance}>Compute variance</Button>
          {variance ? (
            <Typography variant="body2">
              Expected {variance.total_expected} · Actual {variance.total_actual} · Variance {variance.total_variance} ({variance.reporting_currency})
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>

      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Delete line?"
        message="Remove this budget line?"
        confirmText="Delete"
        confirmColor="error"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setDeleteId(null)}
      />
    </Dialog>
  );
}