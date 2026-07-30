import React from "react";
import ReactDOM from "react-dom/client";

// UI5 Web Components theming (SAP Fiori). Full launchpad/shell arrives in Phase 8.
import "@ui5/webcomponents-react/dist/Assets.js";
import { ThemeProvider } from "@ui5/webcomponents-react";

import App from "./App.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);