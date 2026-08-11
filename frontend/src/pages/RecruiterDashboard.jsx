import { useEffect, useState } from "react";
import { FiBriefcase, FiUsers, FiCalendar, FiClock } from "react-icons/fi";
import DashboardCard from "../components/DashboardCard";
import LoadingSpinner from "../components/LoadingSpinner";
import EmptyState from "../components/EmptyState";
import MatchMeter from "../components/MatchMeter";
import { getDashboard } from "../services/api";

const ICONS = {
  "Open roles": <FiBriefcase size={16} />,
  "Active candidates": <FiUsers size={16} />,
  "Interviews this week": <FiCalendar size={16} />,
  "Avg. time to hire": <FiClock size={16} />,
};

export default function RecruiterDashboard() {
  const [isLoading, setIsLoading] = useState(true);
  const [candidates, setCandidates] = useState([]);
  const [stats, setStats] = useState([]);
  const [company, setCompany] = useState("Your team");

  useEffect(() => {
    getDashboard("recruiter")
      .then(({ data }) => {
        setCandidates(data.candidates || []);
        setStats(data.stats || []);
        setCompany(data.company || "Your team");
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div>
      <span className="eyebrow">Recruiter dashboard</span>
      <h1 className="mt-2 text-2xl font-semibold">{company} pipeline</h1>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <DashboardCard key={stat.label} label={stat.label} value={stat.value} icon={ICONS[stat.label]} />
        ))}
      </div>

      <div className="mt-10">
        <h2 className="font-display text-lg font-semibold">Ranked candidates</h2>
        <div className="mt-4">
          {isLoading ? (
            <LoadingSpinner fullPage label="Loading candidates" />
          ) : candidates.length === 0 ? (
            <EmptyState title="No candidates yet" description="Candidates will appear here once they apply to your roles." />
          ) : (
            <div className="overflow-hidden rounded-card border border-ink/8 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-ink/8 bg-paper text-xs uppercase tracking-wide text-slate">
                  <tr>
                    <th className="px-5 py-3 font-medium">Candidate</th>
                    <th className="px-5 py-3 font-medium">Role</th>
                    <th className="px-5 py-3 font-medium">Stage</th>
                    <th className="px-5 py-3 font-medium">Match</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/8">
                  {candidates.map((c) => (
                    <tr key={c.id}>
                      <td className="px-5 py-3.5 font-medium text-ink">{c.name}</td>
                      <td className="px-5 py-3.5 text-slate">{c.role}</td>
                      <td className="px-5 py-3.5">
                        <span className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-medium text-ink">{c.stage}</span>
                      </td>
                      <td className="px-5 py-3.5">
                        <MatchMeter score={c.matchScore} size={40} label="" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
