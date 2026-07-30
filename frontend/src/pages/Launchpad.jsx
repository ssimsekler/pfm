// Overview / launchpad (MUI): KPI cards + balances-by-currency.
import { useEffect, useState } from "react";
import {
  Box, Card, CardActionArea, CardContent, Grid, Typography, CircularProgress, Avatar, Stack,
} from "@mui/material";
import PaymentsIcon from "@mui/icons-material/Payments";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import NotificationsIcon from "@mui/icons-material/Notifications";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { api } from "../api";

function Kpi({ icon, title, value, subtitle, onClick, color }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardActionArea onClick={onClick} sx={{ height: "100%" }}>
        <CardContent>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
            <Avatar sx={{ bgcolor: color || "primary.main" }}>{icon}</Avatar>
            <Typography variant="subtitle1" color="text.secondary">{title}</Typography>
          </Stack>
          <Typography variant="h5">{value}</Typography>
          {subtitle ? <Typography variant="body2" color="text.secondary">{subtitle}</Typography> : null}
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

export default function Launchpad({ navigate }) {
  const [loading, setLoading] = useState(true);
  const [cash, setCash] = useState(null);
  const [worth, setWorth] = useState(null);
  const [notif, setNotif] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const [c, w, n] = await Promise.all([
          api.get("/v1/reports/cash-position").catch(() => null),
          api.get("/v1/reports/net-worth").catch(() => null),
          api.get("/v1/notifications", { limit: 100 }).catch(() => []),
        ]);
        setCash(c); setWorth(w); setNotif(Array.isArray(n) ? n.length : 0);
      } finally { setLoading(false); }
    })();
  }, []);

  const money = (v, ccy) => {
    if (v === null || v === undefined) return "—";
    return new Intl.NumberFormat("en-US", { style: "currency", currency: ccy || "USD", maximumFractionDigits: 0 }).format(Number(v));
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Overview</Typography>
      {loading ? (
        <CircularProgress />
      ) : (
        <>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Kpi icon={<PaymentsIcon />} title="Cash Position"
                value={money(cash?.total_reporting, cash?.reporting_currency)}
                subtitle={`${cash?.accounts?.length ?? 0} accounts · ${cash?.reporting_currency ?? "USD"}`}
                onClick={() => navigate("accounts")} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Kpi icon={<TrendingUpIcon />} title="Net Worth" color="success.main"
                value={money(worth?.net_worth, worth?.reporting_currency)}
                subtitle={`Investments ${money(worth?.investments, worth?.reporting_currency)}`}
                onClick={() => navigate("investments")} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Kpi icon={<NotificationsIcon />} title="Notifications" color="warning.main"
                value={String(notif)} subtitle="Recent alerts & reminders"
                onClick={() => navigate("notifications")} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Kpi icon={<UploadFileIcon />} title="Import Statement" color="info.main"
                value="Upload" subtitle="PDF · CSV · XLSX" onClick={() => navigate("imports")} />
            </Grid>
          </Grid>

          {cash?.per_currency ? (
            <Card sx={{ mt: 3, maxWidth: 560 }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ mb: 1 }}>Balances by Currency</Typography>
                {Object.entries(cash.per_currency).map(([ccy, amt]) => (
                  <Stack key={ccy} direction="row" justifyContent="space-between" sx={{ py: 0.5 }}>
                    <Typography>{ccy}</Typography>
                    <Typography>{Number(amt).toLocaleString()}</Typography>
                  </Stack>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </>
      )}
    </Box>
  );
}