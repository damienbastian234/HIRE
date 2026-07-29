import { FiCheck } from "react-icons/fi";
import EmptyState from "../components/EmptyState";
import { mockApplications } from "../services/mockData";

function StageTracker({ stages, currentStageIndex, rejected }) {
  return (
    <div className="mt-4 flex items-center">
      {stages.map((stage, i) => {
        const isComplete = i <= currentStageIndex && !rejected;
        const isCurrent = i === currentStageIndex;
        return (
          <div key={stage} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold ${
                  isComplete
                    ? "bg-success text-white"
                    : isCurrent && rejected
                    ? "bg-alert text-white"
                    : "bg-ink/8 text-slate"
                }`}
              >
                {isComplete ? <FiCheck size={12} /> : i + 1}
              </span>
              <span className="whitespace-nowrap text-[11px] text-slate">{stage}</span>
            </div>
            {i < stages.length - 1 && (
              <div className={`mx-1.5 h-0.5 flex-1 ${i < currentStageIndex ? "bg-success" : "bg-ink/8"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function ApplicationStatusPage() {
  return (
    <div className="container-page max-w-2xl py-10">
      <span className="eyebrow">Applications</span>
      <h1 className="mt-2 text-2xl font-semibold">Application status</h1>

      <div className="mt-8 space-y-5">
        {mockApplications.length === 0 ? (
          <EmptyState title="No applications yet" description="Apply to a role to see its progress here." />
        ) : (
          mockApplications.map((app) => (
            <div key={app.id} className="rounded-card border border-ink/8 bg-white p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-display text-base font-semibold text-ink">{app.jobTitle}</p>
                  <p className="text-xs text-slate">
                    {app.company} · Applied {app.appliedOn}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${
                    app.rejected ? "bg-alert/10 text-alert" : "bg-signal/15 text-signal-dark"
                  }`}
                >
                  {app.stage}
                </span>
              </div>
              <StageTracker stages={app.stages} currentStageIndex={app.currentStageIndex} rejected={app.rejected} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
