import { FiAlertTriangle } from "react-icons/fi";
import Button from "./Button";

/**
 * ErrorState
 * Props:
 * - title: string — defaults to "Something went wrong"
 * - description: string
 * - onRetry: () => void — shows a "Try again" button when provided
 */
export default function ErrorState({ title = "Something went wrong", description, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-alert/20 bg-alert/5 px-6 py-14 text-center">
      <FiAlertTriangle className="mb-4 text-alert" size={26} />
      <h3 className="font-display text-base font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1.5 max-w-sm text-sm text-slate">{description}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
