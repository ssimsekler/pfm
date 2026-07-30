// Users admin (#14): list users (local app_user mirror), create users, and
// grant/revoke roles (Owner/Editor/Viewer). Backed by /v1/users in admin.py.
import { useCallback, useEffect, useState } from "react";
import {
  Box, Typography, Card, CardHeader, CardContent, Table, TableBody, TableCell, TableHead,
  TableRow, TextField, Button, Alert, Stack, Chip, MenuItem, IconButton, Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import { api } from "../api";

const ROLES = ["Owner", "Editor", "Viewer"];

export default function Users() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({ name: "", email: "", base_currency: "", role: "" });
  const [grant, setGrant] = useState({}); // user_id -> role to grant

  const load = useCallback(async () => {
    setError(null);
    try {
      setRows(await api.get("/v1/users"));
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const addUser = async () => {
    if (!draft.name) { setError("Enter a name."); return; }
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post("/v1/users", {
        name: draft.name,
        email: draft.email || null,
        base_currency: draft.base_currency || null,
        role: draft.role || null,
      });
      setDraft({ name: "", email: "", base_currency: "", role: "" });
      setMsg("User created.");
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doGrant = async (userId) => {
    const role = grant[userId];
    if (!role) return;
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post(`/v1/users/${userId}/roles`, { role });
      setGrant((g) => ({ ...g, [userId]: "" }));
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doRevoke = async (userId, role) => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.del(`/v1/users/${userId}/roles/${encodeURIComponent(role)}`);
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Users</Typography>
      <Card>
        <CardHeader title="Users & roles" subheader="Manage application users and their roles (Owner/Editor/Viewer)." />
        <CardContent>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell><TableCell>Email</TableCell>
                <TableCell>Base ccy</TableCell><TableCell>Roles</TableCell><TableCell>Grant</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((u) => (
                <TableRow key={u.uuid} hover>
                  <TableCell>{u.name}</TableCell>
                  <TableCell>{u.email || ""}</TableCell>
                  <TableCell>{u.base_currency || ""}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>
                      {(u.roles || []).map((r) => (
                        <Chip key={r} label={r} size="small"
                          onDelete={() => doRevoke(u.uuid, r)}
                          deleteIcon={<CloseIcon />} />
                      ))}
                      {(u.roles || []).length === 0 ? <Typography variant="caption" color="text.secondary">none</Typography> : null}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <TextField select size="small" value={grant[u.uuid] || ""}
                        onChange={(e) => setGrant((g) => ({ ...g, [u.uuid]: e.target.value }))}
                        sx={{ width: 130 }}>
                        <MenuItem value=""><em>Role…</em></MenuItem>
                        {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                      </TextField>
                      <Tooltip title="Grant role">
                        <span>
                          <IconButton size="small" color="primary" disabled={busy || !grant[u.uuid]}
                            onClick={() => doGrant(u.uuid)}>
                            <AddIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={5}><Typography color="text.secondary">No users yet.</Typography></TableCell></TableRow>
              ) : null}
            </TableBody>
          </Table>

          <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>Add a user</Typography>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexWrap: "wrap" }}>
            <TextField label="Name" size="small" value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
            <TextField label="Email" size="small" value={draft.email}
              onChange={(e) => setDraft({ ...draft, email: e.target.value })} />
            <TextField label="Base ccy" size="small" value={draft.base_currency}
              onChange={(e) => setDraft({ ...draft, base_currency: e.target.value })}
              inputProps={{ maxLength: 3, style: { textTransform: "uppercase" } }} sx={{ width: 110 }} />
            <TextField label="Role" size="small" select value={draft.role}
              onChange={(e) => setDraft({ ...draft, role: e.target.value })} sx={{ width: 130 }}>
              <MenuItem value=""><em>None</em></MenuItem>
              {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
            </TextField>
            <Button variant="contained" startIcon={<AddIcon />} onClick={addUser} disabled={busy}>Add</Button>
          </Stack>

          <Alert severity="info" sx={{ mt: 2 }}>
            This manages the application’s user directory and role grants. Sign-in credentials are
            managed by Keycloak; a default <b>admin</b> user (password <code>admin</code>) is seeded
            for first login — change it in Keycloak.
          </Alert>
        </CardContent>
      </Card>
    </Box>
  );
}