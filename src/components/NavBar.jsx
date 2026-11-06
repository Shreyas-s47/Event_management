import React from "react";

export default function Navbar({ user, onLogout }) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">E</span>
        <span className="brand-name">EVENT<span>OPS</span></span>
        <span className="brand-badge">ADMIN CONSOLE</span>
      </div>

      {user && (
        <div className="topbar-user">
          <div className="user-avatar">{user.email.charAt(0).toUpperCase()}</div>
          <div className="user-details">
            <strong>{user.name || "Operations Lead"}</strong>
            <span>{user.email}</span>
          </div>
          <button onClick={onLogout} className="logout-button">
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
