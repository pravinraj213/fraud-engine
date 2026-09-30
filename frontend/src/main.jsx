import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import QueuePage from "./pages/QueuePage.jsx";
import RulesPage from "./pages/RulesPage.jsx";
import SimulatorPage from "./pages/SimulatorPage.jsx";
import TransactionPage from "./pages/TransactionPage.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<QueuePage />} />
          <Route path="transactions/:id" element={<TransactionPage />} />
          <Route path="simulator" element={<SimulatorPage />} />
          <Route path="rules" element={<RulesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
