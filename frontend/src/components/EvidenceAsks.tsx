import { MessageCircleQuestion, Send } from "lucide-react";
import { useState } from "react";
import { api, type EvidenceRequest } from "../api";
import { auditStatus, auditTime } from "../auditStatus";
import SkillName from "./SkillName";

/** One ask row: the question, its status, and the answer once given. */
function AskRow({ request, showSkill }: { request: EvidenceRequest; showSkill: boolean }) {
  const meta = auditStatus(request.status);
  return (
    <li className="ask-row" data-status={request.status}>
      <span className={`status-mark ${meta.className}`}>
        <span className="status-dot" aria-hidden="true" />{meta.label}
      </span>
      <div className="ask-body">
        <p>
          {showSkill && <strong><SkillName item={{ skill_id: request.skill_id }} />: </strong>}
          {request.note || "The recruiter asked for more evidence on this skill."}
        </p>
        {request.response && <p className="ask-answer">{request.response}</p>}
      </div>
      <time dateTime={request.status === "responded" && request.responded_at ? request.responded_at : request.created_at}>
        {auditTime(request.status === "responded" && request.responded_at ? request.responded_at : request.created_at)}
      </time>
    </li>
  );
}

/** Student side: every recruiter ask on this passport, with an answer box for open ones. */
export function EvidenceQuestions({ passportId, requests, onChanged }: {
  passportId: string;
  requests: EvidenceRequest[];
  onChanged: () => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  if (requests.length === 0) return null;
  const open = requests.filter((item) => item.status === "open");
  const answered = requests.filter((item) => item.status === "responded");
  const respond = async (requestId: string) => {
    const response = (drafts[requestId] ?? "").trim();
    if (!response) return;
    setBusyId(requestId);
    setError("");
    try {
      await api.respondEvidence(passportId, requestId, response);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send the answer.");
    } finally {
      setBusyId(null);
    }
  };
  return (
    <section className="panel ask-panel" aria-live="polite">
      <div className="panel-heading">
        <div><div className="eyebrow">FROM THE RECRUITER</div><h2>Questions about your evidence</h2></div>
        {open.length > 0 && <span className="count-tag">{open.length} to answer</span>}
      </div>
      <ol className="ask-list">
        {open.map((request) => (
          <li className="ask-row" data-status="open" key={request.id}>
            <span className="status-mark status-request">
              <span className="status-dot" aria-hidden="true" />Request
            </span>
            <div className="ask-body">
              <p><strong><SkillName item={{ skill_id: request.skill_id }} />: </strong>
                {request.note || "The recruiter asked for more evidence on this skill."}</p>
              <div className="review-form-row">
                <label className="review-note">
                  <span>Your answer</span>
                  <input
                    type="text" value={drafts[request.id] ?? ""} maxLength={2000}
                    placeholder="Share a link, a repo, a short explanation…"
                    onChange={(event) => setDrafts((current) => ({ ...current, [request.id]: event.target.value }))}
                  />
                </label>
                <div className="review-actions">
                  <button className="button review-decide" disabled={busyId === request.id || !(drafts[request.id] ?? "").trim()}
                    onClick={() => respond(request.id)}>
                    <Send size={14} /> Send answer
                  </button>
                </div>
              </div>
            </div>
            <time dateTime={request.created_at}>{auditTime(request.created_at)}</time>
          </li>
        ))}
        {answered.map((request) => <AskRow request={request} showSkill key={request.id} />)}
      </ol>
      {error && <p className="notice notice-error">{error}</p>}
    </section>
  );
}

/** Recruiter side: asks for the selected skill, and the composer to ask for more. */
export function EvidenceAskPanel({ passportId, skillId, requests, readOnly, onChanged }: {
  passportId: string;
  skillId: string;
  requests: EvidenceRequest[];
  readOnly?: boolean;
  onChanged: () => void;
}) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const forSkill = requests.filter((item) => item.skill_id === skillId);
  const openAsk = forSkill.find((item) => item.status === "open");
  const ask = () => {
    setBusy(true);
    setError("");
    api.askEvidence(passportId, { skill_id: skillId, note: note.trim() })
      .then(() => { setNote(""); onChanged(); })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setBusy(false));
  };
  if (forSkill.length === 0 && readOnly) return null;
  return (
    <section className="panel ask-panel" aria-live="polite">
      <div className="panel-heading">
        <div><h2>Ask the candidate</h2></div>
        {forSkill.length > 0 && <span className="count-tag">{forSkill.length}</span>}
      </div>
      {forSkill.length > 0 && (
        <ol className="ask-list">
          {forSkill.map((request) => <AskRow request={request} showSkill={false} key={request.id} />)}
        </ol>
      )}
      {!readOnly && !openAsk && (
        <div className="review-form-row">
          <label className="review-note">
            <span>Question</span>
            <input
              type="text" value={note} maxLength={1000}
              placeholder="What would you like the candidate to show?"
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <div className="review-actions">
            <button className="button review-decide" disabled={busy} onClick={ask}>
              <MessageCircleQuestion size={14} /> Ask for evidence
            </button>
          </div>
        </div>
      )}
      {!readOnly && openAsk && <p className="muted">One question is still waiting for an answer.</p>}
      {error && <p className="notice notice-error">{error}</p>}
    </section>
  );
}
