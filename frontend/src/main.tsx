import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Providers } from "./app/providers";
import { App } from "./App";
import { ErrorBoundary } from "./shared/ui/WorkspaceUi";
import "./styles/global.css";
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <Providers>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </Providers>
    </ErrorBoundary>
  </StrictMode>,
);
