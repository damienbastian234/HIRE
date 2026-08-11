/**
 * DashboardCard
 * Props:
 * - label: string
 * - value: string | number
 * - icon: ReactNode
 * - trend: string — optional small caption, e.g. "+3 this week"
 *
 * Usage: <DashboardCard label="Applications" value={12} icon={<FiSend />} />
 */
export default function DashboardCard({ label, value, icon, trend }) {
  return (
    <div className="rounded-card border border-ink/8 bg-white p-5 shadow-card">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate">{label}</span>
        {icon && <span className="text-signal-dark">{icon}</span>}
      </div>
      <p className="mt-3 font-display text-2xl font-semibold text-ink">{value}</p>
      {trend && <p className="mt-1 text-xs text-success">{trend}</p>}
    </div>
  );
}
