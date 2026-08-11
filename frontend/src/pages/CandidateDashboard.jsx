import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiSend, FiCalendar, FiAward, FiTarget, FiArrowRight } from "react-icons/fi";
import DashboardCard from "../components/DashboardCard";
import MatchMeter from "../components/MatchMeter";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import useAuth from "../hooks/useAuth";
import { getDashboard } from "../services/api";

const ICONS = { Applications: <FiSend size={16} />, Interviews: <FiCalendar size={16} />, Offers: <FiAward size={16} />, "Profile match": <FiTarget size={16} /> };

export default function CandidateDashboard() {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState([]);

  useEffect(() => {
    getDashboard("candidate")
      .then(({ data }) => {
        setApplications(data.applications || []);
        setStats(data.stats || []);
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div>
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <span className="eyebrow">Candidate dashboard</span>
          <h1 className="mt-2 text-2xl font-semibold">Welcome back, {user?.name?.split(" ")[0] || "there"}</h1>
        </div>
        <MatchMeter score={92} label="profile" />
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <DashboardCard key={stat.label} label={stat.label} value={stat.value} icon={ICONS[stat.label]} />
        ))}
      </div>

      <div className="mt-10">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold">Recent applications</h2>
          <Link to="/application-status" className="flex items-center gap-1 text-sm font-medium text-ink hover:text-signal-dark">
            View all <FiArrowRight size={14} />
          </Link>
        </div>

        <div className="mt-4">
          {isLoading ? (
            <LoadingSpinner fullPage label="Loading applications" />
          ) : applications.length === 0 ? (
            <EmptyState
              title="No applications yet"
              description="Browse open roles and apply — your status will show up here."
              action={
                <Link to="/jobs">
                  <span className="text-sm font-medium text-signal-dark">Browse jobs</span>
                </Link>
              }
            />
          ) : (
            <div className="divide-y divide-ink/8 rounded-card border border-ink/8 bg-white">
              {applications.map((app) => (
                <div key={app.id} className="flex items-center justify-between gap-4 px-5 py-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{app.jobTitle}</p>
                    <p className="text-xs text-slate">{app.company}</p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${
                      app.rejected ? "bg-alert/10 text-alert" : "bg-signal/15 text-signal-dark"
                    }`}
                  >
                    {app.stage}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
