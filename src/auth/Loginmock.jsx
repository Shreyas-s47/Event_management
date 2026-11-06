import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function LoginMock({ onLogin }) {
  const [email, setEmail] = useState("admin@eventops.io");
  const [password, setPassword] = useState("admin123");
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simulate successful login authentication
    onLogin({ id: "usr-01", email, role: "admin" });
    navigate("/admin");
  };

  return (
    <div className="login-page">
      <div className="login-orbit orbit-one" />
      <div className="login-orbit orbit-two" />
      <div className="login-layout">
        <section className="login-intro">
          <span className="eyebrow">WELCOME BACK</span>
          <h1>Make every event <em>unforgettable.</em></h1>
          <p>One calm, beautiful command center for every detail that makes your events matter.</p>
          <div className="intro-stat"><strong>24/7</strong><span>Event operations visibility</span></div>
        </section>
        <section className="login-card">
          <div className="login-card-header">
            <span className="login-icon">E</span>
            <div><h2>Sign in to EventOps</h2><p>Access your admin workspace</p></div>
          </div>
          <form onSubmit={handleSubmit} className="login-form">
            <div className="field">
              <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            </div>
            <button type="submit" className="primary-button">Enter workspace <span>→</span></button>
          </form>
          <p className="demo-note">Demo access is pre-filled for your convenience.</p>
        </section>
      </div>
    </div>
  );
}