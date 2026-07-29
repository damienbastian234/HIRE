import { forwardRef, useId } from "react";

/**
 * Input
 * Props:
 * - label: string — visible label text
 * - error: string — validation message; also sets aria-invalid
 * - hint: string — helper text shown when there is no error
 * - all other props pass through to the native <input>
 */
const Input = forwardRef(function Input({ label, error, hint, className = "", id, ...rest }, ref) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const descriptionId = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-ink">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={descriptionId}
        className={`w-full rounded-xl border bg-white px-4 py-2.5 text-sm text-ink placeholder:text-slate-light
          focus:outline-none focus:ring-2 focus:ring-signal-dark/60 focus:border-signal-dark/60
          ${error ? "border-alert" : "border-ink/12"} ${className}`}
        {...rest}
      />
      {error ? (
        <p id={descriptionId} className="text-xs text-alert">
          {error}
        </p>
      ) : hint ? (
        <p id={descriptionId} className="text-xs text-slate">
          {hint}
        </p>
      ) : null}
    </div>
  );
});

export default Input;
