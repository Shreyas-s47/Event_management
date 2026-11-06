import React, { useState } from "react";
import { MOCK_EVENTS } from "../mockData";
import { Card, StatusBadge } from "../../components/UIComponents.jsx";

export default function AdminDashboard() {
  const [events, setEvents] = useState(MOCK_EVENTS);
  const [statusFilter, setStatusFilter] = useState("All events");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newEventName, setNewEventName] = useState("");

  const visibleEvents = events.filter((event) => {
    if (statusFilter === "Approved") return event.status === "Approved";
    if (statusFilter === "Pending") return event.status === "Pending Approval";
    return true;
  });

  const toggleApproval = (id) => {
    setEvents((prev) =>
      prev.map((evt) =>
        evt.id === id
          ? {
              ...evt,
              status: evt.status === "Approved" ? "Pending Approval" : "Approved",
            }
          : evt
      )
    );
  };

  const createEvent = (event) => {
    event.preventDefault();
    const name = newEventName.trim();
    if (!name) return;

    setEvents((prev) => [
      ...prev,
      {
        id: `evt-${String(Date.now()).slice(-3)}`,
        name,
        host: "New client",
        date: "2026-12-31",
        status: "Pending Approval",
        budget: "$0",
        venue: "To be confirmed",
      },
    ]);
    setNewEventName("");
    setShowCreateForm(false);
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <span className="eyebrow">THURSDAY, NOVEMBER 06, 2026</span>
          <h1>Good afternoon, <em>Operations Lead.</em></h1>
          <p>Here is what is happening across your event universe today.</p>
        </div>
        <button className="outline-button" onClick={() => setShowCreateForm((open) => !open)}>
          + Create event
        </button>
      </header>

      {showCreateForm && (
        <form className="create-event-form" onSubmit={createEvent}>
          <label htmlFor="new-event-name">Event name</label>
          <input
            id="new-event-name"
            value={newEventName}
            onChange={(event) => setNewEventName(event.target.value)}
            placeholder="e.g. Product launch night"
            autoFocus
            required
          />
          <button type="submit" className="primary-button">Add event <span>→</span></button>
        </form>
      )}

      <div className="metrics-grid">
        <Card className="metric-card metric-purple">
          <span className="metric-icon">✦</span>
          <p className="metric-label">Total events</p>
          <p className="metric-value">{events.length}</p>
          <span className="metric-trend">↗ 12% <small>vs last month</small></span>
        </Card>
        <Card className="metric-card metric-green">
          <span className="metric-icon">✓</span>
          <p className="metric-label">Approved events</p>
          <p className="metric-value">
            {events.filter((e) => e.status === "Approved").length}
          </p>
          <span className="metric-trend">↗ 8% <small>vs last month</small></span>
        </Card>
        <Card className="metric-card metric-orange">
          <span className="metric-icon">◷</span>
          <p className="metric-label">Pending reviews</p>
          <p className="metric-value">
            {events.filter((e) => e.status === "Pending Approval").length}
          </p>
          <span className="metric-trend neutral">Needs your attention</span>
        </Card>
      </div>

      <Card className="events-panel">
        <div className="panel-heading">
          <div><h2>Master event list</h2><p>Keep track of every event in your portfolio.</p></div>
          <select
            className="filter-button"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label="Filter events by status"
          >
            <option>All events</option>
            <option value="Approved">Approved</option>
            <option value="Pending">Pending</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="events-table">
            <thead>
              <tr>
                <th>Event name</th><th>Host client</th><th>Date</th><th>Venue</th><th>Budget</th><th>Status</th><th />
              </tr>
            </thead>
            <tbody>
              {visibleEvents.map((evt) => (
                <tr key={evt.id}>
                  <td className="event-name">{evt.name}<small>{evt.id.toUpperCase()}</small></td>
                  <td>{evt.host}</td><td>{evt.date}</td><td>{evt.venue}</td><td className="budget">{evt.budget}</td><td>
                    <StatusBadge status={evt.status} />
                  </td>
                  <td className="action-cell">
                    <button onClick={() => toggleApproval(evt.id)} className="row-action" aria-label={`Toggle status for ${evt.name}`}>•••</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {visibleEvents.length === 0 && <p className="empty-state">No events match this filter.</p>}
        </div>
      </Card>
    </div>
  );
}