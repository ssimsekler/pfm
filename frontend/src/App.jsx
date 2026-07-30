import { useEffect, useState } from "react";
import {
  ShellBar,
  Card,
  CardHeader,
  Text,
  FlexBox,
  FlexBoxDirection,
  BusyIndicator,
} from "@ui5/webcomponents-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

// Phase 0 placeholder shell. The full Fiori launchpad (tiles, routing,
// list reports, object pages) is built in Phase 8.
export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable" }));
  }, []);

  return (
    <>
      <ShellBar primaryTitle="PFM — Personal Finance Management" />
      <FlexBox
        direction={FlexBoxDirection.Column}
        style={{ padding: "1rem", gap: "1rem" }}
      >
        <Card
          header={
            <CardHeader
              titleText="Welcome"
              subtitleText="Phase 0 — Foundation scaffold"
            />
          }
        >
          <div style={{ padding: "1rem" }}>
            <Text>
              This is the initial application shell. Accounts, transactions,
              budgeting, investments, imports, and reports are delivered in
              subsequent phases (see docs/PLAN.md).
            </Text>
          </div>
        </Card>

        <Card
          header={<CardHeader titleText="Backend status" />}
        >
          <div style={{ padding: "1rem" }}>
            {health ? (
              <Text>
                API: {health.status}
                {health.version ? ` (v${health.version})` : ""}
              </Text>
            ) : (
              <BusyIndicator active />
            )}
          </div>
        </Card>
      </FlexBox>
    </>
  );
}