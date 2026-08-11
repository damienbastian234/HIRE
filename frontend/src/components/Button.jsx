import { forwardRef } from "react";

const VARIANTS = {
  primary: "bg-ink text-paper hover:bg-ink-700 focus-visible:ring-ink",
  signal: "bg-signal text-ink hover:bg-signal-dark focus-visible:ring-signal-dark",
  outline: "border border-ink/15 text-ink hover:border-ink/40 bg-transparent",
  ghost: "text-ink hover:bg-ink/5 bg-transparent",
  danger: "bg-alert text-white hover:bg-alert/90",
};

const SIZES = {
  sm: "text-sm px-3.5 py-2",
  md: "text-sm px-5 py-2.5",
  lg: "text-base px-6 py-3.5",
};

/**
 * Button
 * Props:
 * - variant: "primary" | "signal" | "outline" | "ghost" | "danger"
 * - size: "sm" | "md" | "lg"
 * - isLoading: boolean — shows an inline spinner and disables the button
 * - as: "button" | "a" — renders an anchor when needed
 */
const Button = forwardRef(function Button(
  { variant = "primary", size = "md", isLoading = false, className = "", children, disabled, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors duration-150
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-paper
        disabled:opacity-50 disabled:cursor-not-allowed
        ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {isLoading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" />
      )}
      {children}
    </button>
  );
});

export default Button;
