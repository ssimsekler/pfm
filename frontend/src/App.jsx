import { useEffect, useState } from "react";
import {
  HashRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  ListSubheader,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
} from "@mui/material";
import HomeIcon from "@mui/icons-material/Home";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import SavingsIcon from "@mui/icons-material/Savings";
import CategoryIcon from "@mui/icons-material/Category";
import AssessmentIcon from "@mui/icons-material/Assessment";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import NotificationsIcon from "@mui/icons-material/Notifications";
import SettingsIcon from "@mui/icons-material/Settings";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

import { initAuth, getUser, login, logout, passwordLogin } from "./auth";
import Launchpad from "./pages/Launchpad";
import Transactions from "./pages/Transactions";
import CashFlowItems from "./pages/CashFlowItems";
import RecurringItems from "./pages/RecurringItems";
import Budgets from "./pages/Budgets";
import EntityList from "./pages/EntityList";
import Reports from "./pages/Reports";
import Imports from "./pages/Imports";
import Notifications from "./pages/Notifications";
import Configuration from "./pages/Configuration";
import Settings from "./pages/Settings";
import Users from "./pages/Users";
import Help from "./pages/Help";
import Export from "./pages/Export";
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Alert, Stack } from "@mui/material";
import PeopleIcon from "@mui/icons-material/People";

const DRAWER_WIDTH = 250;

// key -> element renderer. Each screen has its own URL (#/key).
const SCREENS = {
  home: (nav) => <Launchpad navigate={nav} />,
  transactions: () => <Transactions />,
  accounts: () => <EntityList entity="accounts" />,
  institutions: () => <EntityList entity="institutions" />,
  partners: () => <EntityList entity="partners" />,
  beneficiaries: () => <EntityList entity="beneficiaries" />,
  "expense-categories": () => <EntityList entity="expense-categories" />,
  "cash-flow-items": () => <CashFlowItems />,
  recurring: () => <RecurringItems />,
  investments: () => <EntityList entity="investments" />,
  loans: () => <EntityList entity="loans" />,
  "installment-plans": () => <EntityList entity="installment-plans" />,
  goals: () => <EntityList entity="goals" />,
  budgets: () => <Budgets />,
  reports: () => <Reports />,
  imports: () => <Imports />,
  notifications: () => <Notifications />,
  configuration: () => <Configuration />,
  settings: () => <Settings />,
  profile: () => <Settings section="profile" />,
  users: () => <Users />,
  help: () => <Help />,
  export: () => <Export />,
};

// Sidebar structure: groups of { label, key, icon }.
const NAV = [
  { label: "Overview", key: "home", icon: <HomeIcon /> },
  { label: "Transactions", key: "transactions", icon: <ReceiptLongIcon /> },
  {
    subheader: "Money",
    items: [
      { label: "Accounts", key: "accounts", icon: <AccountBalanceIcon /> },
      { label: "Investments", key: "investments", icon: <SavingsIcon /> },
      { label: "Loans", key: "loans", icon: <AccountBalanceIcon /> },
      { label: "Installments", key: "installment-plans", icon: <ReceiptLongIcon /> },
      { label: "Goals", key: "goals", icon: <SavingsIcon /> },
    ],
  },
  {
    subheader: "Master Data",
    items: [
      { label: "Institutions", key: "institutions", icon: <AccountBalanceIcon /> },
      { label: "Partners", key: "partners", icon: <CategoryIcon /> },
      { label: "Beneficiaries", key: "beneficiaries", icon: <CategoryIcon /> },
      { label: "Categories", key: "expense-categories", icon: <CategoryIcon /> },
      { label: "Cash Flow Items", key: "cash-flow-items", icon: <CategoryIcon /> },
    ],
  },
  {
    subheader: "Planning",
    items: [
      { label: "Recurring", key: "recurring", icon: <ReceiptLongIcon /> },
      { label: "Budgets", key: "budgets", icon: <AssessmentIcon /> },
      { label: "Reports", key: "reports", icon: <AssessmentIcon /> },
    ],
  },
  { label: "Imports", key: "imports", icon: <UploadFileIcon /> },
  { label: "Export", key: "export", icon: <DownloadIcon /> },
  { label: "Notifications", key: "notifications", icon: <NotificationsIcon /> },
  { label: "Configuration", key: "configuration", icon: <SettingsIcon /> },
  { label: "Settings", key: "settings", icon: <SettingsIcon /> },
  { label: "Users", key: "users", icon: <PeopleIcon /> },
  { label: "Help", key: "help", icon: <HelpOutlineIcon /> },
];

function PasswordLoginDialog({ open, onClose }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true); setError(null);
    try {
      await passwordLogin(username, password);
      window.location.reload();
    } catch (e) { setError(e.message); setBusy(false); }
  }

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Sign in</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <TextField label="Username" size="small" value={username}
            onChange={(e) => setUsername(e.target.value)} autoFocus />
          <TextField label="Password" type="password" size="small" value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
      </DialogActions>
    </Dialog>
  );
}

function Shell({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const route = location.pathname.replace(/^\//, "") || "home";
  const go = (key) => navigate("/" + key);
  const [anchorEl, setAnchorEl] = useState(null);
  const [loginOpen, setLoginOpen] = useState(false);

  const navItem = (item) => (
    <ListItemButton
      key={item.key}
      selected={route === item.key}
      onClick={() => go(item.key)}
      sx={{ borderRadius: 1, mx: 1 }}
    >
      <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
      <ListItemText primary={item.label} />
    </ListItemButton>
  );

  return (
    <Box sx={{ display: "flex", height: "100vh" }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 0, mr: 1 }}>PFM</Typography>
          <Typography variant="body2" sx={{ flexGrow: 1, opacity: 0.8 }}>
            Personal Finance Management
          </Typography>
          <IconButton color="inherit" onClick={() => go("notifications")} size="large">
            <NotificationsIcon />
          </IconButton>
          <IconButton color="inherit" onClick={(e) => setAnchorEl(e.currentTarget)} size="large">
            <Avatar sx={{ width: 32, height: 32, bgcolor: "secondary.main" }}>
              {(user.name || "U").slice(0, 1).toUpperCase()}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
            <MenuItem disabled>
              <Box>
                <Typography variant="subtitle2">{user.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {user.authenticated ? (user.roles || []).join(", ") || "no roles" : "Not signed in"}
                </Typography>
              </Box>
            </MenuItem>
            <Divider />
            {user.authenticated ? (
              [
                <MenuItem key="profile" onClick={() => { setAnchorEl(null); go("profile"); }}>My Profile</MenuItem>,
                <MenuItem key="logout" onClick={() => { setAnchorEl(null); logout(); }}>Sign out</MenuItem>,
              ]
            ) : (
              [
                <MenuItem key="sso" onClick={() => { setAnchorEl(null); login(); }}>Sign in (SSO)</MenuItem>,
                <MenuItem key="pwd" onClick={() => { setAnchorEl(null); setLoginOpen(true); }}>Sign in with password</MenuItem>,
              ]
            )}
          </Menu>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: "auto", py: 1 }}>
          <List dense>
            {NAV.map((entry, idx) =>
              entry.items ? (
                <li key={entry.subheader}>
                  <ul style={{ padding: 0 }}>
                    <ListSubheader disableSticky>{entry.subheader}</ListSubheader>
                    {entry.items.map(navItem)}
                  </ul>
                </li>
              ) : (
                navItem(entry)
              )
            )}
          </List>
        </Box>
      </Drawer>

      <PasswordLoginDialog open={loginOpen} onClose={() => setLoginOpen(false)} />

      <Box component="main" sx={{ flexGrow: 1, height: "100vh", overflow: "auto", bgcolor: "background.default" }}>
        <Toolbar />
        <Box sx={{ p: 3 }}>
          <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            {Object.entries(SCREENS).map(([key, render]) => (
              <Route key={key} path={"/" + key} element={render(go)} />
            ))}
            <Route path="*" element={<Typography>Not found</Typography>} />
          </Routes>
        </Box>
      </Box>
    </Box>
  );
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState({ name: "…", roles: [], authenticated: false });

  useEffect(() => {
    (async () => {
      await initAuth();
      setUser(getUser());
      setReady(true);
    })();
  }, []);

  if (!ready) {
    return <Box sx={{ p: 4 }}>Loading…</Box>;
  }

  return (
    <HashRouter>
      <Shell user={user} />
    </HashRouter>
  );
}