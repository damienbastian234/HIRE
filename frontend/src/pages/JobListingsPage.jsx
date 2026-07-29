import { useMemo, useState } from "react";
import { FiSearch } from "react-icons/fi";
import JobCard from "../components/JobCard";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import { mockJobs } from "../services/mockData";

const TYPES = ["All", "Full-time", "Contract"];

export default function JobListingsPage() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All");
  const [isLoading] = useState(false);

  const filtered = useMemo(() => {
    return mockJobs.filter((job) => {
      const matchesQuery =
        job.title.toLowerCase().includes(query.toLowerCase()) ||
        job.company.toLowerCase().includes(query.toLowerCase());
      const matchesType = type === "All" || job.type === type;
      return matchesQuery && matchesType;
    });
  }, [query, type]);

  return (
    <div className="container-page py-10">
      <span className="eyebrow">Job listings</span>
      <h1 className="mt-2 text-2xl font-semibold">Find your next role</h1>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <FiSearch className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-light" size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title or company"
            aria-label="Search jobs"
            className="w-full rounded-full border border-ink/12 bg-white py-2.5 pl-10 pr-4 text-sm focus:border-signal-dark/60 focus:outline-none focus:ring-2 focus:ring-signal-dark/60"
          />
        </div>
        <div className="flex gap-2">
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                type === t ? "bg-ink text-paper" : "bg-white text-slate border border-ink/12"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8">
        {isLoading ? (
          <LoadingSpinner fullPage label="Loading jobs" />
        ) : filtered.length === 0 ? (
          <EmptyState title="No roles match your search" description="Try a different keyword or clear the filter." />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
