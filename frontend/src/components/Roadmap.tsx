import type { Roadmap as RoadmapData } from "../api";

const EFFORT_LABEL: Record<string, string> = { S: "Short", M: "Medium", L: "Long" };

/** The structured readiness roadmap: ordered phases of numbered steps, built from role gaps. */
export default function Roadmap({ roadmap }: { roadmap: RoadmapData }) {
  if (roadmap.empty) {
    return <div className="empty-state">No open gaps for this role. Keep building and re-check when your work changes.</div>;
  }
  return (
    <div className="roadmap">
      {roadmap.phases.map((phase) => (
        <section className="roadmap-phase" key={phase.phase}>
          <h3>Phase {phase.phase} · {phase.title}</h3>
          <p className="muted">{phase.why}</p>
          {phase.steps.map((step) => (
            <article className="roadmap-step" key={step.order}>
              <div className="roadmap-step-head">
                <span className="roadmap-order">{step.order}</span>
                <strong>{step.title}</strong>
                <span className={`effort-tag effort-${step.effort}`} title={roadmap.effort_legend[step.effort]}>
                  {EFFORT_LABEL[step.effort] ?? step.effort}
                </span>
                {step.importance === "must" && <span className="must-tag">MUST</span>}
              </div>
              <p className="muted">Now: {step.current} · Target: {step.target_level}</p>
              <ol className="roadmap-actions">
                {step.actions.map((action, index) => <li key={index}>{action}</li>)}
              </ol>
            </article>
          ))}
        </section>
      ))}
    </div>
  );
}
