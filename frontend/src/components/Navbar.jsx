import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { FiMenu, FiX } from "react-icons/fi";
import { AnimatePresence, motion } from "framer-motion";
import Button from "./Button";
import useAuth from "../hooks/useAuth";

const LINKS = [
  { to: "/jobs", label: "Jobs" },
  { to: "/dashboard", label: "Dashboard" },
];

/**
 * Navbar
 * No required props. Reads auth state via useAuth to swap CTA between
 * "Sign in / Get started" and a signed-in link to the dashboard.
 */
export default function Navbar() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, user, signOut } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-ink/8 bg-paper/90 backdrop-blur">
      <nav className="container-page flex h-16 items-center justify-between" aria-label="Primary">
        <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold text-ink">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink text-signal">H</span>
          H.I.R.E.
        </Link>

        <div className="hidden items-center gap-7 md:flex">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors ${isActive ? "text-ink" : "text-slate hover:text-ink"}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          {isAuthenticated ? (
            <>
              <span className="text-sm text-slate">Hi, {user.name.split(" ")[0]}</span>
              <Button variant="outline" size="sm" onClick={signOut}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-slate hover:text-ink">
                Sign in
              </Link>
              <Link to="/register">
                <Button variant="signal" size="sm">
                  Get started
                </Button>
              </Link>
            </>
          )}
        </div>

        <button
          className="p-2 text-ink md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <FiX size={22} /> : <FiMenu size={22} />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-ink/8 bg-paper md:hidden"
          >
            <div className="container-page flex flex-col gap-4 py-5">
              {LINKS.map((link) => (
                <Link key={link.to} to={link.to} onClick={() => setOpen(false)} className="text-sm font-medium text-ink">
                  {link.label}
                </Link>
              ))}
              <div className="mt-2 flex flex-col gap-2">
                {isAuthenticated ? (
                  <Button variant="outline" size="sm" onClick={signOut}>
                    Sign out
                  </Button>
                ) : (
                  <>
                    <Link to="/login" onClick={() => setOpen(false)} className="text-sm font-medium text-ink">
                      Sign in
                    </Link>
                    <Link to="/register" onClick={() => setOpen(false)}>
                      <Button variant="signal" size="sm" className="w-full">
                        Get started
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
