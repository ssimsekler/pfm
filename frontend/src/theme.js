// Finance-style MUI theme (ADR: UX migrated to MUI).
import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0a3d62", light: "#3c6382", dark: "#062c48", contrastText: "#fff" },
    secondary: { main: "#1e88e5" },
    success: { main: "#2e7d32" },
    warning: { main: "#ed6c02" },
    error: { main: "#c62828" },
    info: { main: "#0277bd" },
    background: { default: "#f4f6f8", paper: "#ffffff" },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: `"Inter", "Segoe UI", Roboto, Arial, sans-serif`,
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiCard: { defaultProps: { elevation: 1 }, styleOverrides: { root: { borderRadius: 10 } } },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiAppBar: { styleOverrides: { root: { backgroundImage: "none" } } },
  },
});

export default theme;