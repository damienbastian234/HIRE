/**
 * EmptyState
 * Props:
 * - icon: ReactNode — icon element, e.g. <FiInbox size={28} />
 * - title: string
 * - description: string
 * - action: ReactNode — optional CTA, e.g. a <Button>
 */
export default function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-ink/15 px-6 py-14 text-center">
      {icon && <div className="mb-4 text-slate-light">{icon}</div>}
      <h3 className="font-display text-base font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1.5 max-w-sm text-sm text-slate">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
