import { History } from "lucide-react";
import { useState } from "react";
import type { AuditEvent } from "../api";
import { auditStatus, auditTime } from "../auditStatus";

const TRAIL_FILTERS = [
  { value: "all", label: "All events" },
  { value: "verified", label: "Verified" },
  { value: "flagged", label: "Flagged" },
  { value: "rejected", label: "Rejected" },
  { value: "requests", label: "Review requests" },
];

const matchesFilter = (event: AuditEvent, filter: string) => {
  if (filter === "all") return true;
  if (filter === "requests") return event.kind !== "evidence_review";
  return event.kind === "evidence_review" && event.status === filter;
};

/** Append-only record of every review decision and review request on a passport. */
export default function AuditTrail({ trail }: { trail: AuditEvent[] }) {
  const [filter, setFilter] = useState("all");
  const visible = trail.filter((event) => matchesFilter(event, filter));
  const filterLabel = TRAIL_FILTERS.find((item) => item.value === filter)?.label.toLowerCase() ?? "";
  return (
    <section className="panel audit-panel" aria-live="polite">
      <div className="panel-heading">
        <div><h2>Audit trail</h2></div>
        <div className="audit-tools">
          <label className="audit-filter">
            <span>Show</span>
            <select className="filter-select" value={filter} aria-label="Filter audit events"
              onChange={(event) => setFilter(event.target.value)}>
              {TRAIL_FILTERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <span className="count-tag">{filter === "all" ? `${trail.length} events` : `${visible.length} of ${trail.length}`}</span>
        </div>
      </div>
      <p className="muted audit-explainer">Every review decision and review request on this passport, oldest first. Decisions are never edited; a changed mind is a new event.</p>
      {visible.length ? (
        <ol className="audit-list">
          {visible.map((event, index) => {
            const meta = auditStatus(event.status);
            return (
              <li className="audit-row" key={`${event.at}-${index}`}>
                <span className={`status-mark ${meta.className}`}>
                  <span className="status-dot" aria-hidden="true" />{meta.label}
                </span>
                <div className="audit-body">
                  <p><strong>{event.actor}</strong> {event.summary}</p>
                  {event.note ? <p className="audit-note">{event.note}</p> : null}
                </div>
                <time dateTime={event.at}>{auditTime(event.at)}</time>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className="empty-state audit-empty">
          <History size={18} aria-hidden="true" />
          <p>No {filterLabel} events yet.</p>
          <small>Verify, flag or reject evidence above and every decision lands here, oldest first.</small>
        </div>
      )}
    </section>
  );
}
