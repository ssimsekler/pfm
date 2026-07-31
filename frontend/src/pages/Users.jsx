// Users admin (#14 + Session 815 Item 6/9/10/11/12): list users (local app_user
// mirror) with a Username column, create users (username min length 3), grant/
// revoke roles (Admin/Editor/Viewer), and deactivate/reactivate/remove users.
// Backed by /v1/users in admin.py.
import { useCallback, useEffect, useState } from "react";
import {
  Box, Typography, Card, CardHeader, CardContent, Table, TableBody, TableCell, TableHead,
  TableRow, TextField, Button, Alert, Stack, Chip, MenuItem, IconButton, Tooltip,
  FormControlLabel, Switch,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteIcon from "@mui/icons-material/Delete";
import ConfirmDialog from "../components/ConfirmDialog";
import { api } from "../api";

const ROLES = ["Admin", "Editor", "Viewer"];

export default function Users() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [draft, setDraft] = useState({ username: "", name: "", email: "", base_currency: "", role: "", password: "" });
  const [grant, setGrant] = useState({}); // user_id -> role to grant
  const [tempPassword, setTempPassword] = useState(null); // shown once after create
  const [confirmDelete, setConfirmDelete] = useState(null); // user row pending hard delete

  const load = useCallback(async () => {
    setError(null);
    try {
      setRows(await api.get("/v1/users", { include_inactive: showInactive ? "true" : "" }));
    } catch (e) { setError(e.message); }
  }, [showInactive]);

  useEffect(() => { load(); }, [load]);

  const usernameError = draft.username.length > 0 && draft.username.trim().length < 3;

  const addUser = async () => {
    if (draft.username.trim().length < 3) { setError("Username must be at least 3 characters."); return; }
    setBusy(true); setError(null); setMsg(null); setTempPassword(null);
    try {
      const created = await api.post("/v1/users", {
        username: draft.username.trim(),
        name: draft.name || null,
        email: draft.email || null,
        base_currency: draft.base_currency || null,
        role: draft.role || null,
        password: draft.password || null,
      });
      setDraft({ username: "", name: "", email: "", base_currency: "", role: "", password: "" });
      setMsg(`User “${created.username || created.name || created.uuid}” created in Keycloak.`);
      if (created && created.temp_password) setTempPassword(created.temp_password);
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

  const setActive = async (u, active) => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post(`/v1/users/${u.uuid}/${active ? "reactivate" : "deactivate"}`);
      setMsg(active ? "User reactivated." : "User deactivated.");
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doDelete = async () => {
    const u = confirmDelete;
    if (!u) return;
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.del(`/v1/users/${u.uuid}`);
      setConfirmDelete(null);
      setMsg("User removed.");
      await load();
    } catch (e) { setError(e.message); setConfirmDelete(null); } finally { setBusy(false); }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Users</Typography>
      <Card>
        <CardHeader title="Users & roles" subheader="Manage application users and their roles (Admin/Editor/Viewer)." />
        <CardContent>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}

          <FormControlLabel
            control={<Switch checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />}
            label="Show deactivated users"
            sx={{ mb: 1 }}
          />

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Username</TableCell><TableCell>Name</TableCell><TableCell>Email</TableCell>
                <TableCell>Base ccy</TableCell><TableCell>Status</TableCell>
                <TableCell>Roles</TableCell><TableCell>Grant</TableCell><TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((u) => (
                <TableRow key={u.uuid} hover sx={{ opacity: u.active === false ? 0.55 : 1 }}>
                  <TableCell><code>{u.username || "—"}</code></TableCell>
                  <TableCell>{u.name}</TableCell>
                  <TableCell>{u.email || ""}</TableCell>
                  <TableCell>{u.base_currency || ""}</TableCell>
                  <TableCell>
                    {u.active === false
                      ? <Chip size="small" label="Inactive" color="default" />
                      : <Chip size="small" label="Active" color="success" variant="outlined" />}
                  </TableCell>
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
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      {u.active === false ? (
                        <Tooltip title="Reactivate">
                          <span>
                            <IconButton size="small" color="success" disabled={busy}
                              onClick={() => setActive(u, true)}>
                              <CheckCircleIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      ) : (
                        <Tooltip title="Deactivate">
                          <span>
                            <IconButton size="small" color="warning" disabled={busy}
                              onClick={() => setActive(u, false)}>
                              <BlockIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                      <Tooltip title="Remove user">
                        <span>
                          <IconButton size="small" color="error" disabled={busy}
                            onClick={() => { setError(null); setConfirmDelete(u); }}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={8}><Typography color="text.secondary">No users yet.</Typography></TableCell></TableRow>
              ) : null}
            </TableBody>
          </Table>

          {tempPassword ? (
            <Alert severity="warning" sx={{ mt: 2 }} onClose={() => setTempPassword(null)}>
              Temporary password (shown once — hand it to the user; they must change it on first
              login): <code>{tempPassword}</code>
            </Alert>
          ) : null}

          <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>Add a user</Typography>
          <Stack direction="row" spacing={1.5} alignItems="flex-start" sx={{ flexWrap: "wrap" }}>
            <TextField label="Username" size="small" required value={draft.username}
              error={usernameError} helperText={usernameError ? "Min 3 characters" : " "}
              onChange={(e) => setDraft({ ...draft, username: e.target.value })} />
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
            <TextField label="Password (optional)" size="small" type="password" value={draft.password}
              onChange={(e) => setDraft({ ...draft, password: e.target.value })}
              helperText="Leave blank to auto-generate" sx={{ width: 180 }} />
            <Button variant="contained" startIcon={<AddIcon />} onClick={addUser}
              disabled={busy || draft.username.trim().length < 3}>Add</Button>
          </Stack>

          <Alert severity="info" sx={{ mt: 2 }}>
            Creating a user provisions a full <b>Keycloak</b> account (username, temporary password,
            role) and mirrors it here. Deactivate disables sign-in (keeps the record); Remove deletes
            the Keycloak account and the local mirror.
          </Alert>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title="Remove user?"
        message={confirmDelete
          ? `Permanently remove "${confirmDelete.username || confirmDelete.name || confirmDelete.uuid}"? This deletes the Keycloak account and the local record. Consider Deactivate instead if you may need it later.`
          : ""}
        confirmText="Remove"
        confirmColor="error"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </Box>
  );
}
