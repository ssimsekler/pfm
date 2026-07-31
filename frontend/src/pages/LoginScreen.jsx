// Full-screen login (Session 815, Batch 9). Replaces the login dialog.
// Modes: sign-in, change-password, forgot (request reset), reset (confirm token).
// The "Forgot password?" link is only shown when the app's SMTP is configured
// (auth/config.email_enabled). The local admin fallback works even if Keycloak
// is down — the backend tries it first.
import { useEffect, useState } from "react";
import {
  Box, Paper, Stack, TextField, Button, Typography, Alert, Link, Divider,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import {
  passwordLogin, login as ssoLogin, getAuthConfig,
  changePassword, requestPasswordReset, confirmPasswordReset,
} from "../auth";

export default function LoginScreen() {
  const [mode, setMode] = useState("signin"); // signin | change | forgot | reset
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [emailEnabled, setEmailEnabled] = useState(false);

  useEffect(() => {
    getAuthConfig().then((c) => setEmailEnabled(Boolean(c && c.email_enabled)));
  }, []);

  const reset = () => { setError(null); setInfo(null); };

  async function doSignIn() {
    reset(); setBusy(true);
    try {
      await passwordLogin(username, password);
      window.location.reload();
    } catch (e) { setError(e.message); setBusy(false); }
  }

  async function doChange() {
    reset();
    if (newPassword !== confirmPass) { setError("New passwords don't match."); return; }
    setBusy(true);
    try {
      await changePassword(username, oldPassword, newPassword);
      setInfo("Password changed. Please sign in with your new password.");
      setMode("signin"); setPassword(""); setOldPassword(""); setNewPassword(""); setConfirmPass("");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  async function doForgot() {
    reset(); setBusy(true);
    try {
      await requestPasswordReset(username);
      setInfo("If an email is on file, a reset token has been sent. Enter it below.");
      setMode("reset");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  async function doReset() {
    reset();
    if (newPassword !== confirmPass) { setError("New passwords don't match."); return; }
    setBusy(true);
    try {
      await confirmPasswordReset(token, newPassword);
      setInfo("Password reset. Please sign in.");
      setMode("signin"); setToken(""); setNewPassword(""); setConfirmPass("");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  const onEnter = (fn) => (e) => { if (e.key === "Enter") fn(); };

  return (
    <Box
      sx={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        bgcolor: "background.default", p: 2,
      }}
    >
      <Paper elevation={3} sx={{ p: 4, width: "100%", maxWidth: 420 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <LockOutlinedIcon color="primary" />
            <Box>
              <Typography variant="h5">PFM</Typography>
              <Typography variant="body2" color="text.secondary">
                Personal Finance Management
              </Typography>
            </Box>
          </Stack>

          {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
          {info ? <Alert severity="success" onClose={() => setInfo(null)}>{info}</Alert> : null}

          {mode === "signin" && (
            <>
              <Typography variant="h6">Sign in</Typography>
              <TextField label="Username" size="small" fullWidth autoFocus
                value={username} onChange={(e) => setUsername(e.target.value)}
                onKeyDown={onEnter(doSignIn)} />
              <TextField label="Password" type="password" size="small" fullWidth
                value={password} onChange={(e) => setPassword(e.target.value)}
                onKeyDown={onEnter(doSignIn)} />
              <Button variant="contained" fullWidth disabled={busy} onClick={doSignIn}>
                {busy ? "Signing in…" : "Sign in"}
              </Button>
              <Stack direction="row" justifyContent="space-between">
                <Link component="button" type="button" underline="hover"
                  onClick={() => { reset(); setMode("change"); }}>
                  Change password
                </Link>
                {emailEnabled ? (
                  <Link component="button" type="button" underline="hover"
                    onClick={() => { reset(); setMode("forgot"); }}>
                    Forgot password?
                  </Link>
                ) : null}
              </Stack>
              <Divider>or</Divider>
              <Button variant="outlined" fullWidth onClick={ssoLogin}>
                Sign in with SSO (Keycloak)
              </Button>
            </>
          )}

          {mode === "change" && (
            <>
              <Typography variant="h6">Change password</Typography>
              <TextField label="Username" size="small" fullWidth autoFocus
                value={username} onChange={(e) => setUsername(e.target.value)} />
              <TextField label="Current password" type="password" size="small" fullWidth
                value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
              <TextField label="New password" type="password" size="small" fullWidth
                value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              <TextField label="Confirm new password" type="password" size="small" fullWidth
                value={confirmPass} onChange={(e) => setConfirmPass(e.target.value)}
                onKeyDown={onEnter(doChange)} />
              <Button variant="contained" fullWidth disabled={busy} onClick={doChange}>
                {busy ? "Saving…" : "Change password"}
              </Button>
              <Link component="button" type="button" underline="hover"
                onClick={() => { reset(); setMode("signin"); }}>
                ← Back to sign in
              </Link>
            </>
          )}

          {mode === "forgot" && (
            <>
              <Typography variant="h6">Reset password</Typography>
              <Typography variant="body2" color="text.secondary">
                Enter your username. If an email is on file, we'll send a reset token.
              </Typography>
              <TextField label="Username" size="small" fullWidth autoFocus
                value={username} onChange={(e) => setUsername(e.target.value)}
                onKeyDown={onEnter(doForgot)} />
              <Button variant="contained" fullWidth disabled={busy} onClick={doForgot}>
                {busy ? "Sending…" : "Send reset token"}
              </Button>
              <Stack direction="row" justifyContent="space-between">
                <Link component="button" type="button" underline="hover"
                  onClick={() => { reset(); setMode("signin"); }}>
                  ← Back to sign in
                </Link>
                <Link component="button" type="button" underline="hover"
                  onClick={() => { reset(); setMode("reset"); }}>
                  I have a token
                </Link>
              </Stack>
            </>
          )}

          {mode === "reset" && (
            <>
              <Typography variant="h6">Enter reset token</Typography>
              <TextField label="Reset token" size="small" fullWidth autoFocus
                value={token} onChange={(e) => setToken(e.target.value)} />
              <TextField label="New password" type="password" size="small" fullWidth
                value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              <TextField label="Confirm new password" type="password" size="small" fullWidth
                value={confirmPass} onChange={(e) => setConfirmPass(e.target.value)}
                onKeyDown={onEnter(doReset)} />
              <Button variant="contained" fullWidth disabled={busy} onClick={doReset}>
                {busy ? "Resetting…" : "Reset password"}
              </Button>
              <Link component="button" type="button" underline="hover"
                onClick={() => { reset(); setMode("signin"); }}>
                ← Back to sign in
              </Link>
            </>
          )}
        </Stack>
      </Paper>
    </Box>
  );
}