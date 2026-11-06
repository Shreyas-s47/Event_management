import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/NavBar.jsx";
import LoginMock from "./auth/Loginmock";
import AdminDashboard from "./auth/admin/AdminDashboard";
import { MOCK_USER } from "./auth/mockData";
import "./App.css";

export default function App() {
  const [user, setUser] = useState(MOCK_USER);

  const handleLogout = () => setUser(null);
  const handleLogin = (userData) => setUser(userData);

  return (
    <Router>
      <div className="app-shell">
        <Navbar user={user} onLogout={handleLogout} />
        <main className="app-main">
          <Routes>
            <Route
              path="/login"
              element={
                !user ? (
                  <LoginMock onLogin={handleLogin} />
                ) : (
                  <Navigate to="/admin" replace />
                )
              }
            />
            <Route
              path="/admin"
              element={
                user ? <AdminDashboard /> : <Navigate to="/login" replace />
              }
            />
            <Route path="*" element={<Navigate to="/admin" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}