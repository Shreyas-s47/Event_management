import React from "react";

export function Card({ title, children, className = "" }) {
  return (
    <div className={`panel ${className}`}>
      {title && <h3 className="panel-title">{title}</h3>}
      {children}
    </div>
  );
}

export function StatusBadge({ status }) {
  const isApproved = status === "Approved";
  return (
    <span className={`status-badge ${isApproved ? "approved" : "pending"}`}>
      <span className="status-dot" />
      {status}
    </span>
  );
}
