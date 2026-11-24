import * as React from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "danger" | "pill";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant = "default",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses =
      "inline-flex items-center justify-center font-medium transition-colors select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer";

    const variantClasses = {
      default:
        "bg-[var(--accent)] text-[var(--accent-foreground)] hover:opacity-90 active:scale-[0.98] border border-transparent shadow-none",
      secondary:
        "bg-[var(--soft-surface)] text-[var(--foreground)] hover:bg-[var(--border)] active:scale-[0.98] border border-[var(--border)]",
      outline:
        "bg-transparent text-[var(--foreground)] border border-[var(--border)] hover:bg-[var(--soft-surface)] active:scale-[0.98]",
      ghost:
        "bg-transparent text-[var(--foreground)] hover:bg-[var(--soft-surface)] active:scale-[0.98] border border-transparent",
      danger:
        "bg-[var(--risk-high-bg)] text-[var(--risk-high-text)] border border-[var(--risk-high-border)] hover:opacity-90 active:scale-[0.98]",
      pill:
        "bg-[var(--accent)] text-[var(--accent-foreground)] rounded-full hover:opacity-90 active:scale-[0.98] border border-transparent",
    }[variant];

    const sizeClasses = {
      sm: "h-8 px-3 text-xs gap-1.5 rounded-[10px]",
      md: "h-10 px-4 text-sm gap-2 rounded-[10px]",
      lg: "h-11 px-5 text-base gap-2.5 rounded-[10px]",
      icon: "h-9 w-9 p-0 rounded-[10px]",
    }[size];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className}`}
        {...props}
      >
        {isLoading && <Loader2 className="h-4 w-4 animate-spin shrink-0" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
