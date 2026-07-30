import { useEffect, useState } from "react";
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

const ROUTES = {
  home: (nav) => <Launchpad navigate={nav} />,
  transactions: () => <Transactions />,
  accounts: () => <EntityList entity="accounts" />,
  partners: () => <EntityList entity="partners" />,
  beneficiaries: () => <EntityList entity="beneficiaries" />,
  "expense-categories": () => <EntityList entity="expense-categories" />,
  "cash-flow-items": () => <EntityList entity="cash-flow-items" />,
  investments: () => <EntityList entity="investments" />,
  loans: () => <EntityList entity="loans" />,
  "installment-plans": () => <EntityList entity="installment-plans" />,
  goals: () => <EntityList entity="goals" />,
  budgets: () => <EntityList entity="budgets" />,
  reports: () => <Reports />,
  imports: () => <Imports />,
  notifications: () => <Notifications />,
  configuration: () => <Configuration />,
  export: () => <Export />,
};

export default function App() {
  const [route, setRoute] = useState("home");
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState({ name: "…", roles: [] });
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    (async () => {
      await initAuth();
      setUser(getUser());
      setReady(true);
    })();
  }, []);

  const nav = (key) => setRoute(key);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <ShellBar
        primaryTitle="PFM"
        secondaryTitle="Personal Finance Management"
        showNotifications
        onNotificationsClick={() => nav("notifications")}
        profile={<Avatar icon="employee" />}
        onProfileClick={() => setProfileOpen(true)}
      >
        <ShellBarItem icon="home" text="Overview" onClick={() => nav("home")} />
        <ShellBarItem icon="excel-attachment" text="Export" onClick={() => nav("export")} />
      </ShellBar>

      <Popover open={profileOpen} onAfterClose={() => setProfileOpen(false)} headerText={user.name}>
        <List
          onItemClick={(e) => {
            const action = e.detail.item.dataset.action;
            setProfileOpen(false);
            if (action === "login") login();
            if (action === "logout") logout();
          }}
        >
          <StandardListItem data-action="login">Sign in</StandardListItem>
          <StandardListItem data-action="logout">Sign out</StandardListItem>
        </List>
      </Popover>

      <FlexBox style={{ flex: 1, minHeight: 0 }}>
        <SideNavigation
          style={{ width: "260px", flexShrink: 0 }}
          onSelectionChange={(e) => {
            const key = e.detail.item.dataset.route;
            if (key) nav(key);
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
          {ready ? (ROUTES[route] ? ROUTES[route](nav) : <div>Not found</div>) : <div>Loading…</div>}
        </div>
      </FlexBox>
    </div>
  );
}