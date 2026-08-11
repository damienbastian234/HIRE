/**
 * MatchMeter
 * Signature visual for H.I.R.E. — a radial "fit" indicator shared by the hero,
 * job cards, and dashboards so the idea of a match score reads consistently
 * everywhere it appears.
 *
 * Props:
 * - score: number (0-100)
 * - size: number — diameter in px (default 88)
 * - label: string — small caption under the score (default "match")
 */
export default function MatchMeter({ score = 0, size = 88, label = "match" }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference - (clamped / 100) * circumference;
  const color = clamped >= 80 ? "#3FAE7A" : clamped >= 55 ? "#F2A93B" : "#E15C4E";

  return (
    <div className="relative inline-flex flex-col items-center justify-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" width={size} height={size} className="-rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#E7E4DA" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ "--offset": offset }}
          className="animate-dash"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-xl font-semibold leading-none text-ink">{clamped}%</span>
        <span className="mt-1 text-[10px] uppercase tracking-wide text-slate">{label}</span>
      </div>
    </div>
  );
}
