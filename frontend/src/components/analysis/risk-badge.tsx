import * as React from "react";
import { RiskChip } from "@/components/ui/risk-chip";

export function RiskBadge({
  category,
  score,
  className,
}: {
  category: string;
  score?: number;
  className?: string;
}) {
  return <RiskChip category={category} score={score} className={className} />;
}

export { RiskChip };
