import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import SessionPage from "./pages/Session";
import Report from "./pages/Report";
import Label from "./pages/Label";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/session/:id" element={<SessionPage />} />
        <Route path="/report/:id" element={<Report />} />
        <Route path="/label" element={<Label />} />
        <Route path="/label/:id" element={<Label />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
