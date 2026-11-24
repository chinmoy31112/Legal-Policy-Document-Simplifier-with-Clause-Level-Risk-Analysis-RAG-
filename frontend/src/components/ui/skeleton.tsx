import * as React from "react";

export function Skeleton({
  className = "",
  rounded = "inner",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  rounded?: "inner" | "card" | "full";
}) {
  const radiusClass = {
    inner: "rounded-[10px]",
    card: "rounded-[18px]",
    full: "rounded-full",
  }[rounded];

  return (
    <div
      className={`animate-pulse bg-[var(--soft-surface)] opacity-70 ${radiusClass} ${className}`}
      aria-hidden="true"
      {...props}
    />
  );
}
