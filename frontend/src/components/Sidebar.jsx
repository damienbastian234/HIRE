import { NavLink } from "react-router-dom";

/**
 * Sidebar
 * Props:
 * - items: { to: string, label: string, icon: ReactNode }[]
 *
 * Usage:
 * <Sidebar items={[{ to: "/dashboard", label: "Overview", icon: <FiGrid /> }]} />
 */
export default function Sidebar({ items = [] }) {
  return (
    <aside className="hidden w-56 shrink-0 border-r border-ink/8 py-8 pr-4 md:block">
      <nav className="flex flex-col gap-1" aria-label="Dashboard">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors ${
                isActive ? "bg-ink text-paper" : "text-slate hover:bg-ink/5 hover:text-ink"
              }`
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
