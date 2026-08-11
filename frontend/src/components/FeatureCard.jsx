import { motion } from "framer-motion";

/**
 * FeatureCard
 * Props:
 * - icon: ReactNode
 * - title: string
 * - description: string
 * - index: number — used to stagger the entrance animation
 *
 * Usage:
 * <FeatureCard icon={<FiZap />} title="Instant scoring" description="..." index={0} />
 */
export default function FeatureCard({ icon, title, description, index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: "easeOut" }}
      className="rounded-card border border-ink/8 bg-white p-6 shadow-card"
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-signal/15 text-signal-dark">
        {icon}
      </div>
      <h3 className="mt-4 font-display text-base font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 text-sm text-slate">{description}</p>
    </motion.div>
  );
}
