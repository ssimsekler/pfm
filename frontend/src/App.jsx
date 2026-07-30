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
  ShellBar,
  ShellBarItem,
  SideNavigation,
  SideNavigationItem,
  SideNavigationSubItem,
  FlexBox,
  Avatar,
  Popover,
  List,
  StandardListItem,
  Title,
  Text,
} from "@ui5/webcomponents-react";
import "@ui5/webcomponents-icons/dist/AllIcons.js";

import { initAuth, getUser, login, logout } from "./auth";
import Launchpad from "./pages/Launchpad";
import Transactions from "./pages/Transactions";
import EntityList from "./pages/EntityList";
import Reports from "./pages/Reports";
import Imports from "./pages/Imports";
import Notifications from "./pages/Notifications";
import Configuration from "./pages/Configuration";
import Export from "./pages/Export";

// Route key → element. Each screen has its own URL (#/key) so browser
// Back/Forward and refresh work (#3).
const SCREENS = {
  home: { label: "Overview", element: (nav) => <Launchpad navigate={nav} /> },
  transactions: { label: "Transactions", element: () => <Transactions /> },
  accounts: { label: "Accounts", element: () => <EntityList entity="accounts" /> },
  institutions: { label: "Institutions", element: () => <EntityList entity="institutions" /> },
  partners: { label: "Partners", element: () => <EntityList entity="partners" /> },
  beneficiaries: { label: "Beneficiaries", element: () => <EntityList entity="beneficiaries" /> },
  "expense-categories": { label: "Categories", element: () => <EntityList entity="expense-categories" /> },
  "cash-flow-items": { label: "Cash Flow Items", element: () => <EntityList entity="cash-flow-items" /> },
  investments: { label: "Investments", element: () => <EntityList entity="investments" /> },
  loans: { label: "Loans", element: () => <EntityList entity="loans" /> },
  "installment-plans": { label: "Installments", element: () => <EntityList entity="installment-plans" /> },
  goals: { label: "Goals", element: () => <EntityList entity="goals" /> },
  budgets: { label: "Budgets", element: () => <EntityList entity="budgets" /> },
  reports: { label: "Reports", element: () => <Reports /> },
  imports: { label: "Imports", element: () => <Imports /> },
  notifications: { label: "Notifications", element: () => <Notifications /> },
  configuration: { label: "Configuration", element: () => <Configuration /> },
  export: { label: "Export", element: () => <Export /> },
};

function Shell({ user, onProfile, profileOpen, setProfileOpen }) {
  const navigate = useNavigate();
  const location = useLocation();
  const route = location.pathname.replace(/^\//, "") || "home";
  const go = (key) => navigate("/" + key);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <ShellBar
        primaryTitle="PFM"
        secondaryTitle="Personal Finance Management"
        showNotifications
        onNotificationsClick={() => go("notifications")}
        profile={<Avatar icon="employee" />}
        onProfileClick={onProfile}
      >
        <ShellBarItem icon="home" text="Overview" onClick={() => go("home")} />
        <ShellBarItem icon="excel-attachment" text="Export" onClick={() => go("export")} />
      </ShellBar>

      <Popover
        open={profileOpen}
        onAfterClose={() => setProfileOpen(false)}
        headerText={user.name}
        opener="pfm-avatar-opener"
      >
        <div style={{ padding: "0.5rem 0.75rem", minWidth: "220px" }}>
          <Title level="H6">{user.name}</Title>
          {user.email ? <Text style={{ display: "block" }}>{user.email}</Text> : null}
          <Text style={{ display: "block", color: "var(--sapNeutralTextColor)", marginTop: "0.25rem" }}>
            {user.authenticated ? `Roles: ${(user.roles || []).join(", ") || "—"}` : "Not signed in"}
          </Text>
          <List
            style={{ marginTop: "0.5rem" }}
            onItemClick={(e) => {
              const action = e.detail.item.dataset.action;
              setProfileOpen(false);
              if (action === "login") login();
              if (action === "logout") logout();
              if (action === "profile") go("configuration");
            }}
          >
            {user.authenticated ? (
              <>
                <StandardListItem icon="person-placeholder" data-action="profile">My Profile</StandardListItem>
                <StandardListItem icon="log" data-action="logout">Sign out</StandardListItem>
              </>
            ) : (
              <StandardListItem icon="log" data-action="login">Sign in</StandardListItem>
            )}
          </List>
        </div>
      </Popover>

      <FlexBox style={{ flex: 1, minHeight: 0 }}>
        <SideNavigation
          style={{ width: "260px", flexShrink: 0 }}
          onSelectionChange={(e) => {
            const key = e.detail.item.dataset.route;
            if (key) go(key);
          }}
        >
          <SideNavigationItem text="Overview" icon="home" data-route="home" selected={route === "home"} />
          <SideNavigationItem text="Transactions" icon="journey-arrive" data-route="transactions" selected={route === "transactions"} />
          <SideNavigationItem text="Money" icon="wallet" expanded>
            <SideNavigationSubItem text="Accounts" data-route="accounts" selected={route === "accounts"} />
            <SideNavigationSubItem text="Investments" data-route="investments" selected={route === "investments"} />
            <SideNavigationSubItem text="Loans" data-route="loans" selected={route === "loans"} />
            <SideNavigationSubItem text="Installments" data-route="installment-plans" selected={route === "installment-plans"} />
            <SideNavigationSubItem text="Goals" data-route="goals" selected={route === "goals"} />
          </SideNavigationItem>
          <SideNavigationItem text="Master Data" icon="dimension" expanded>
            <SideNavigationSubItem text="Institutions" data-route="institutions" selected={route === "institutions"} />
            <SideNavigationSubItem text="Partners" data-route="partners" selected={route === "partners"} />
            <SideNavigationSubItem text="Beneficiaries" data-route="beneficiaries" selected={route === "beneficiaries"} />
            <SideNavigationSubItem text="Categories" data-route="expense-categories" selected={route === "expense-categories"} />
            <SideNavigationSubItem text="Cash Flow Items" data-route="cash-flow-items" selected={route === "cash-flow-items"} />
          </SideNavigationItem>
          <SideNavigationItem text="Planning" icon="business-objects-experience" expanded>
            <SideNavigationSubItem text="Budgets" data-route="budgets" selected={route === "budgets"} />
            <SideNavigationSubItem text="Reports" data-route="reports" selected={route === "reports"} />
          </SideNavigationItem>
          <SideNavigationItem text="Imports" icon="add-document" data-route="imports" selected={route === "imports"} />
          <SideNavigationItem text="Export" icon="excel-attachment" data-route="export" selected={route === "export"} />
          <SideNavigationItem text="Notifications" icon="bell" data-route="notifications" selected={route === "notifications"} />
          <SideNavigationItem text="Configuration" icon="action-settings" data-route="configuration" selected={route === "configuration"} />
        </SideNavigation>

        <div style={{ flex: 1, overflow: "auto", padding: "1rem 1.5rem", background: "var(--sapBackgroundColor)" }}>
          <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            {Object.entries(SCREENS).map(([key, s]) => (
              <Route key={key} path={"/" + key} element={s.element(go)} />
            ))}
            <Route path="*" element={<div>Not found</div>} />
          </Routes>
        </div>
      </FlexBox>
    </div>
  );
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState({ name: "…", roles: [], authenticated: false });
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    (async () => {
      await initAuth();
      setUser(getUser());
      setReady(true);
    })();
  }, []);

  if (!ready) {
    return <div style={{ padding: "2rem" }}>Loading…</div>;
  }

  return (
    <HashRouter>
      <Shell
        user={user}
        profileOpen={profileOpen}
        setProfileOpen={setProfileOpen}
        onProfile={() => setProfileOpen((o) => !o)}
      />
    </HashRouter>
  );
}