import { Link } from "react-router-dom";
import { FiMapPin, FiClock } from "react-icons/fi";
import MatchMeter from "./MatchMeter";

/**
 * JobCard
 * Props:
 * - job: { id, title, company, location, type, salaryRange, postedDaysAgo, matchScore, tags }
 *
 * Usage: <JobCard job={job} />
 */
export default function JobCard({ job }) {
  return (
    <Link
      to={`/jobs/${job.id}`}
      className="block rounded-card border border-ink/8 bg-white p-5 shadow-card transition-shadow hover:shadow-pop focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-dark/60"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate font-display text-base font-semibold text-ink">{job.title}</h3>
          <p className="text-sm text-slate">{job.company}</p>
        </div>
        <MatchMeter score={job.matchScore} size={56} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate">
        <span className="flex items-center gap-1.5">
          <FiMapPin size={13} /> {job.location}
        </span>
        <span className="flex items-center gap-1.5">
          <FiClock size={13} /> Posted {job.postedDaysAgo}d ago
        </span>
        <span className="rounded-full bg-ink/5 px-2 py-0.5 font-medium text-ink">{job.type}</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {job.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-signal/12 px-2.5 py-1 text-xs font-medium text-signal-dark">
            {tag}
          </span>
        ))}
      </div>

      <div className="mt-4 border-t border-ink/8 pt-3 text-sm font-medium text-ink">{job.salaryRange}</div>
    </Link>
  );
}
