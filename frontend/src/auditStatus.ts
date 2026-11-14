/** Shared presentation for audit-trail and review statuses: one dot + word language,
 *  colored with the site's semantic tokens, never a pill badge. */
export const AUDIT_STATUS: Record<string, { label: string; className: string }> = {
  verified: { label: "Verified", className: "status-verified" },
  flagged: { label: "Flagged", className: "status-flagged" },
  rejected: { label: "Rejected", className: "status-rejected" },
  open: { label: "Request", className: "status-request" },
  reviewed: { label: "Closed", className: "status-closed" },
};

export const auditStatus = (status: string) =>
  AUDIT_STATUS[status] ?? { label: status, className: "status-closed" };

const auditTimeFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export const auditTime = (iso: string) => auditTimeFormat.format(new Date(iso));
