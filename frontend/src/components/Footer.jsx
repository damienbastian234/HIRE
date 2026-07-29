import { Link } from "react-router-dom";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Job listings", to: "/jobs" },
      { label: "Candidate dashboard", to: "/dashboard" },
      { label: "AI interview", to: "/interview" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Sign in", to: "/login" },
      { label: "Create account", to: "/register" },
      { label: "Profile", to: "/profile" },
    ],
  },
];

/**
 * Footer
 * No required props. Static site footer with nav columns and legal line.
 */
export default function Footer() {
  return (
    <footer className="border-t border-ink/8 bg-ink text-paper/80">
      <div className="container-page grid gap-10 py-14 sm:grid-cols-2 md:grid-cols-4">
        <div className="md:col-span-2">
          <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold text-paper">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal text-ink">H</span>
            H.I.R.E.
          </Link>
          <p className="mt-3 max-w-sm text-sm text-paper/60">
            Hiring Intelligence & Recruitment Engine — matching candidates to roles with a
            transparent, explainable fit score instead of a keyword filter.
          </p>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.title}>
            <h4 className="eyebrow text-signal-light">{col.title}</h4>
            <ul className="mt-3 space-y-2.5">
              {col.links.map((link) => (
                <li key={link.to}>
                  <Link to={link.to} className="text-sm text-paper/70 hover:text-paper">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-paper/10 py-5">
        <p className="container-page text-xs text-paper/50">
          © {new Date().getFullYear()} H.I.R.E. Built for a hackathon MVP.
        </p>
      </div>
    </footer>
  );
}
