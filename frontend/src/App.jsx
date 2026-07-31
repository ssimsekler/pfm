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
import MenuIcon from "@mui/icons-material/Menu";
import Tooltip from "@mui/material/Tooltip";
// Distinct per-item icons (Bug 9)
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import CreditCardIcon from "@mui/icons-material/CreditCard";
import FlagIcon from "@mui/icons-material/Flag";
import BusinessIcon from "@mui/icons-material/Business";
import StorefrontIcon from "@mui/icons-material/Storefront";
import VolunteerActivismIcon from "@mui/icons-material/VolunteerActivism";
import LabelIcon from "@mui/icons-material/Label";
import SyncIcon from "@mui/icons-material/Sync";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PieChartIcon from "@mui/icons-material/PieChart";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";

import { initAuth, getUser, login, logout, passwordLogin } from "./auth";
import { initFormats } from "./format";
import Launchpad from "./pages/Launchpad";
import Transactions from "./pages/Transactions";
import CashFlowItems from "./pages/CashFlowItems";
import RecurringItems from "./pages/RecurringItems";
import Budgets from "./pages/Budgets";
import EntityList from "./pages/EntityList";
import HierarchyList from "./pages/HierarchyList";
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
  beneficiaries: () => <HierarchyList entity="beneficiaries" />,
  "expense-categories": () => <HierarchyList entity="expense-categories" />,
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

// Sidebar structure: groups of { label, key, icon }. Distinct icons per item (Bug 9).
const NAV = [
  { label: "Overview", key: "home", icon: <HomeIcon /> },
  { label: "Transactions", key: "transactions", icon: <ReceiptLongIcon /> },
  {
    subheader: "Money",
    items: [
      { label: "Accounts", key: "accounts", icon: <AccountBalanceIcon /> },
      { label: "Investments", key: "investments", icon: <TrendingUpIcon /> },
      { label: "Loans", key: "loans", icon: <CreditCardIcon /> },
      { label: "Installments", key: "installment-plans", icon: <AccountBalanceWalletIcon /> },
      { label: "Goals", key: "goals", icon: <FlagIcon /> },
    ],
  },
  {
    subheader: "Master Data",
    items: [
      { label: "Institutions", key: "institutions", icon: <BusinessIcon /> },
      { label: "Partners", key: "partners", icon: <StorefrontIcon /> },
      { label: "Beneficiaries", key: "beneficiaries", icon: <VolunteerActivismIcon /> },
      { label: "Categories", key: "expense-categories", icon: <CategoryIcon /> },
      { label: "Cash Flow Items", key: "cash-flow-items", icon: <LabelIcon /> },
    ],
  },
  {
    subheader: "Planning",
    items: [
      { label: "Recurring", key: "recurring", icon: <AutorenewIcon /> },
      { label: "Budgets", key: "budgets", icon: <PieChartIcon /> },
      { label: "Reports", key: "reports", icon: <AssessmentIcon /> },
    ],
  },
  { label: "Imports", key: "imports", icon: <UploadFileIcon /> },
  { label: "Export", key: "export", icon: <DownloadIcon /> },
  { label: "Notifications", key: "notifications", icon: <NotificationsIcon /> },
  { label: "Configuration", key: "configuration", icon: <SyncIcon /> },
  { label: "Settings", key: "settings", icon: <SettingsIcon /> },
  { label: "Users", key: "users", icon: <PeopleIcon /> },
  // Item 2: Help lives in the top toolbar (next to Notifications), not the drawer.
];

const DRAWER_WIDTH_MINI = 60;

function PasswordLoginDialog({ open, onClose, expired }) {
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
      <DialogTitle>{expired ? "Session expired — sign in again" : "Sign in"}</DialogTitle>
      <DialogContent dividers>
        {expired ? <Alert severity="warning" sx={{ mb: 2 }}>Your session expired. Please sign in again to continue.</Alert> : null}
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
  const [sessionExpired, setSessionExpired] = useState(false);
  // Collapsible mini drawer (Bug 24) — persisted across reloads.
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("pfm_nav_collapsed") === "1"
  );
  const toggleCollapsed = () => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem("pfm_nav_collapsed", next ? "1" : "0");
      return next;
    });
  };
  const width = collapsed ? DRAWER_WIDTH_MINI : DRAWER_WIDTH;

  // Session-expiry handler (Session 742, Bug 3): when the API client can't renew
  // the fallback token, it dispatches `pfm:session-expired`. Prompt re-login via
  // the password dialog instead of cascading raw 401 errors on every page.
  useEffect(() => {
    const onExpired = () => { setSessionExpired(true); setLoginOpen(true); };
    window.addEventListener("pfm:session-expired", onExpired);
    return () => window.removeEventListener("pfm:session-expired", onExpired);
  }, []);

  // When collapsed, show icons only with a tooltip carrying the label (Bug 24).
  const navItem = (item) => {
    const button = (
      <ListItemButton
        key={item.key}
        selected={route === item.key}
        onClick={() => go(item.key)}
        sx={{ borderRadius: 1, mx: 1, justifyContent: collapsed ? "center" : "flex-start", px: collapsed ? 1 : 2 }}
      >
        <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, justifyContent: "center" }}>{item.icon}</ListItemIcon>
        {collapsed ? null : <ListItemText primary={item.label} />}
      </ListItemButton>
    );
    return collapsed ? (
      <Tooltip key={item.key} title={item.label} placement="right">{button}</Tooltip>
    ) : button;
  };

  return (
    <Box sx={{ display: "flex", height: "100vh" }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton color="inherit" edge="start" onClick={toggleCollapsed} size="large"
            aria-label="Toggle navigation" sx={{ mr: 1 }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 0, mr: 1 }}>PFM</Typography>
          <Typography variant="body2" sx={{ flexGrow: 1, opacity: 0.8 }}>
            Personal Finance Management
          </Typography>
          <IconButton color="inherit" onClick={() => go("notifications")} size="large">
            <NotificationsIcon />
          </IconButton>
          {/* Item 2: Help moved from the drawer to the toolbar, next to Notifications. */}
          <Tooltip title="Help">
            <IconButton color="inherit" onClick={() => go("help")} size="large" aria-label="Help">
              <HelpOutlineIcon />
            </IconButton>
          </Tooltip>
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
          width,
          flexShrink: 0,
          whiteSpace: "nowrap",
          [`& .MuiDrawer-paper`]: {
            width,
            boxSizing: "border-box",
            overflowX: "hidden",
            transition: (t) => t.transitions.create("width", {
              easing: t.transitions.easing.sharp,
              duration: t.transitions.duration.enteringScreen,
            }),
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: "auto", overflowX: "hidden", py: 1 }}>
          <List dense>
            {NAV.map((entry, idx) =>
              entry.items ? (
                <li key={entry.subheader}>
                  <ul style={{ padding: 0 }}>
                    {collapsed ? <Divider sx={{ my: 0.5 }} />
                      : <ListSubheader disableSticky>{entry.subheader}</ListSubheader>}
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

      <PasswordLoginDialog open={loginOpen} expired={sessionExpired} onClose={() => { setLoginOpen(false); setSessionExpired(false); }} />

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
    // Fail-safe startup: the shell must always render even if auth or format
    // resolution stalls/throws. We guard every step, flip `ready` in a finally,
    // and add a hard timeout so a slow/unreachable backend can never leave the
    // app stuck on "Loading…" (Session 815, Batch 7). dayjs uses its built-in
    // "en" locale — we no longer runtime-import locale packs (English only).
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        setReady(true);
      }
    };
    // Hard fallback: render the shell after 8s no matter what.
    const timer = setTimeout(finish, 8000);
    (async () => {
      try {
        try { await initAuth(); } catch { /* continue as guest */ }
        try { setUser(getUser()); } catch { /* keep default user */ }
        // Bug 21: resolve display formats (profile → settings → defaults).
        try { await initFormats(); } catch { /* fall back to defaults */ }
      } finally {
        clearTimeout(timer);
        finish();
      }
    })();
    return () => clearTimeout(timer);
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