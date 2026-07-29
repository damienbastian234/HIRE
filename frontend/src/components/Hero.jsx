import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { FiArrowRight } from "react-icons/fi";
import Button from "./Button";
import MatchMeter from "./MatchMeter";

/**
 * Hero
 * Props:
 * - eyebrow, title, description: strings
 * - primaryCta: { label, to }
 * - secondaryCta: { label, to }
 * Renders the MatchMeter as its visual thesis — the "score" idea the whole
 * product is built around, shown before the visitor sees any job listing.
 */
export default function Hero({
  eyebrow = "AI-assisted hiring",
  title = "Hiring, scored honestly.",
  description = "H.I.R.E. reads a resume once and tells both sides — candidate and recruiter — exactly why a match works, in plain numbers instead of buzzwords.",
  primaryCta = { label: "Find a role", to: "/register" },
  secondaryCta = { label: "Post a job", to: "/register" },
}) {
  return (
    <section className="container-page grid items-center gap-12 py-16 md:grid-cols-2 md:py-24">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <span className="eyebrow">{eyebrow}</span>
        <h1 className="mt-4 text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl">{title}</h1>
        <p className="mt-5 max-w-md text-base text-slate">{description}</p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link to={primaryCta.to}>
            <Button variant="signal" size="lg">
              {primaryCta.label}
              <FiArrowRight />
            </Button>
          </Link>
          <Link to={secondaryCta.to}>
            <Button variant="outline" size="lg">
              {secondaryCta.label}
            </Button>
          </Link>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut", delay: 0.15 }}
        className="relative flex justify-center md:justify-end"
      >
        <div className="w-full max-w-sm rounded-card border border-ink/8 bg-white p-6 shadow-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-display text-sm font-semibold text-ink">Frontend Engineer, Platform</p>
              <p className="text-xs text-slate">Northwind Labs</p>
            </div>
            <MatchMeter score={92} size={64} />
          </div>
          <div className="mt-5 space-y-2.5 border-t border-ink/8 pt-5">
            {[
              ["Skills overlap", "9 of 10"],
              ["Experience level", "Strong fit"],
              ["Location", "Hybrid match"],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-slate">{label}</span>
                <span className="font-medium text-ink">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
  );
}
