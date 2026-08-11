const SIZES = { sm: "h-4 w-4 border-2", md: "h-7 w-7 border-2", lg: "h-11 w-11 border-[3px]" };

/**
 * LoadingSpinner
 * Props:
 * - size: "sm" | "md" | "lg"
 * - label: string — visually hidden text for screen readers
 * - fullPage: boolean — centers the spinner in a full-height container
 *
 * Usage: <LoadingSpinner size="md" label="Loading jobs" />
 */
export default function LoadingSpinner({ size = "md", label = "Loading", fullPage = false, className = "" }) {
  const spinner = (
    <span
      role="status"
      className={`inline-block animate-spin rounded-full border-signal-dark/25 border-t-signal-dark ${SIZES[size]} ${className}`}
    >
      <span className="sr-only">{label}</span>
    </span>
  );

  if (!fullPage) return spinner;

  return <div className="flex min-h-[40vh] w-full items-center justify-center">{spinner}</div>;
}
