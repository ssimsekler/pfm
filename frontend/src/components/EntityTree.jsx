// Hierarchical tree view for parent/child entities (Session 742, Bug 25):
// used for Expense Categories and Beneficiaries. Builds a tree from the flat
// list (each row has `parent_id`) and renders collapsible nodes with the same
// Edit/Delete actions as the table. Pure MUI primitives — no extra dependency.
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Box, List, ListItemButton, ListItemText, IconButton, Collapse, Stack,
  Tooltip, Typography, Alert, CircularProgress,
} from "@mui/material";
import ExpandMore from "@mui/icons-material/ExpandMore";
import ChevronRight from "@mui/icons-material/ChevronRight";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { api } from "../api";

// Build a tree: [{ ...row, children: [] }] rooted at rows without a parent
// (or whose parent is not present in the set).
function buildTree(rows) {
  const byId = new Map();
  rows.forEach((r) => byId.set(r.uuid, { ...r, children: [] }));
  const roots = [];
  byId.forEach((node) => {
    const pid = node.parent_id;
    if (pid && byId.has(pid)) {
      byId.get(pid).children.push(node);
    } else {
      roots.push(node);
    }
  });
  const sortRec = (list) => {
    list.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    list.forEach((n) => sortRec(n.children));
  };
  sortRec(roots);
  return roots;
}

function TreeNode({ node, depth, onEdit, onDelete }) {
  const [open, setOpen] = useState(depth < 1); // top levels expanded by default
  const hasChildren = node.children && node.children.length > 0;
  return (
    <>
      <ListItemButton
        sx={{ pl: 2 + depth * 2 }}
        onClick={() => hasChildren && setOpen((o) => !o)}
        dense
      >
        <Box sx={{ width: 28, display: "flex", alignItems: "center" }}>
          {hasChildren ? (open ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />) : null}
        </Box>
        <ListItemText
          primary={node.name}
          secondary={node.mnemonic_id}
          primaryTypographyProps={{ variant: "body2" }}
        />
        <Stack direction="row" spacing={0.5} onClick={(e) => e.stopPropagation()}>
          <Tooltip title="Edit">
            <IconButton size="small" onClick={() => onEdit(node)}><EditIcon fontSize="small" /></IconButton>
          </Tooltip>
          <Tooltip title="Delete">
            <IconButton size="small" color="error" onClick={() => onDelete(node)}><DeleteIcon fontSize="small" /></IconButton>
          </Tooltip>
        </Stack>
      </ListItemButton>
      {hasChildren ? (
        <Collapse in={open} timeout="auto" unmountOnExit>
          <List disablePadding dense>
            {node.children.map((c) => (
              <TreeNode key={c.uuid} node={c} depth={depth + 1} onEdit={onEdit} onDelete={onDelete} />
            ))}
          </List>
        </Collapse>
      ) : null}
    </>
  );
}

export default function EntityTree({ path, refreshKey, onEdit, onDelete }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch a large page so the full hierarchy is present for tree building.
      const data = await api.get(path, { limit: 1000, offset: 0 });
      const items = Array.isArray(data) ? data : data.items || [];
      setRows(items);
    } catch (e) {
      setError(e.message);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [path, refreshKey]);

  useEffect(() => { load(); }, [load]);

  const tree = useMemo(() => buildTree(rows), [rows]);

  if (loading) {
    return <Box sx={{ p: 2, display: "flex", justifyContent: "center" }}><CircularProgress size={24} /></Box>;
  }
  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }
  if (tree.length === 0) {
    return <Typography color="text.secondary" sx={{ p: 2 }}>No records yet.</Typography>;
  }

  return (
    <Box sx={{ bgcolor: "background.paper", borderRadius: 1, border: (t) => `1px solid ${t.palette.divider}` }}>
      <List dense>
        {tree.map((n) => (
          <TreeNode key={n.uuid} node={n} depth={0} onEdit={onEdit} onDelete={onDelete} />
        ))}
      </List>
    </Box>
  );
}