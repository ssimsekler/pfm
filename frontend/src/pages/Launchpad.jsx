import { useEffect, useState } from "react";
import {
  FlexBox,
  FlexBoxWrap,
  Card,
  CardHeader,
  Title,
  Text,
  Icon,
  BusyIndicator,
} from "@ui5/webcomponents-react";
import { api } from "../api";

function KpiTile({ icon, title, value, subtitle, onClick }) {
  return (
    <Card
      style={{ flex: "1 1 220px", minWidth: "220px", maxWidth: "320px", cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      header={<CardHeader titleText={title} avatar={<Icon name={icon} />} />}
    >
      <div style={{ padding: "1rem" }}>
        <Title level="H2" style={{ marginBottom: "0.25rem" }}>{value}</Title>
        {subtitle ? (
          <Text style={{ color: "var(--sapNeutralTextColor)" }}>{subtitle}</Text>
        ) : null}
      </div>
    </Card>
  );
}

export default function Launchpad({ navigate }) {
  const [loading, setLoading] = useState(true);
  const [cash, setCash] = useState(null);
  const [worth, setWorth] = useState(null);
  const [notifCount, setNotifCount] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const [c, w, n] = await Promise.all([
          api.get("/v1/reports/cash-position").catch(() => null),
          api.get("/v1/reports/net-worth").catch(() => null),
          api.get("/v1/notifications", { limit: 100 }).catch(() => []),
        ]);
        setCash(c);
        setWorth(w);
        setNotifCount(Array.isArray(n) ? n.length : 0);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const money = (v, ccy) => {
    if (v === null || v === undefined) return "—";
    const n = Number(v);
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: ccy || "USD",
      maximumFractionDigits: 0,
    }).format(n);
  };

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Overview</Title>
      <BusyIndicator active={loading} style={{ width: "100%" }}>
        <FlexBox wrap={FlexBoxWrap.Wrap} style={{ gap: "1rem" }}>
          <KpiTile
            icon="money-bills"
            title="Cash Position"
            value={money(cash?.total_reporting, cash?.reporting_currency)}
            subtitle={(cash?.accounts?.length ?? 0) + " accounts · " + (cash?.reporting_currency ?? "USD")}
            onClick={() => navigate("accounts")}
          />
          <KpiTile
            icon="business-objects-experience"
            title="Net Worth"
            value={money(worth?.net_worth, worth?.reporting_currency)}
            subtitle={"Investments " + money(worth?.investments, worth?.reporting_currency)}
            onClick={() => navigate("investments")}
          />
          <KpiTile
            icon="bell"
            title="Notifications"
            value={String(notifCount)}
            subtitle="Recent alerts & reminders"
            onClick={() => navigate("notifications")}
          />
          <KpiTile
            icon="add-document"
            title="Import Statement"
            value="Upload"
            subtitle="PDF · CSV · XLSX"
            onClick={() => navigate("imports")}
          />
        </FlexBox>

        {cash?.per_currency ? (
          <Card
            style={{ marginTop: "1.5rem", maxWidth: "600px" }}
            header={<CardHeader titleText="Balances by Currency" />}
          >
            <div style={{ padding: "1rem" }}>
              {Object.entries(cash.per_currency).map(([ccy, amt]) => (
                <FlexBox key={ccy} style={{ justifyContent: "space-between", padding: "0.25rem 0" }}>
                  <Text>{ccy}</Text>
                  <Text>{Number(amt).toLocaleString()}</Text>
                </FlexBox>
              ))}
            </div>
          </Card>
        ) : null}
      </BusyIndicator>
    </div>
  );
}