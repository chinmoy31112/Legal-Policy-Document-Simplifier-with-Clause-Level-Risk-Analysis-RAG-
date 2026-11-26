/**
 * Single source of truth for clause risk categorization and clause counts.
 *
 * Ensures the summary badge, viewer filter pills, and stacked breakdown bar
 * agree on exact totals without double-counting overlapping backend keys.
 */

import type { ClauseAnalysis, RiskDistribution } from "@/types/analysis";

export type DetailedRiskKey =
  | "standard"
  | "slightly_unusual"
  | "one_sided"
  | "high_risk"
  | "potentially_unenforceable";

export type FilterBucket = "all" | "high" | "medium" | "standard";

export interface ClauseCounts {
  total: number;
  standard: number;
  slightlyUnusual: number;
  oneSided: number;
  highRisk: number;
  unenforceable: number;
  filterCounts: {
    all: number;
    high: number;
    medium: number;
    standard: number;
  };
}

export function getDetailedRiskKey(riskCategory: string | undefined | null): DetailedRiskKey {
  const cat = String(riskCategory || "standard")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");

  if (cat === "potentially_unenforceable" || cat === "critical") {
    return "potentially_unenforceable";
  }
  if (cat === "high_risk" || cat === "high") {
    return "high_risk";
  }
  if (cat === "one_sided") {
    return "one_sided";
  }
  if (cat === "slightly_unusual" || cat === "unusual" || cat === "medium") {
    return "slightly_unusual";
  }
  return "standard";
}

export function getClauseBucket(riskCategory: string | undefined | null): Exclude<FilterBucket, "all"> {
  const key = getDetailedRiskKey(riskCategory);
  if (key === "high_risk" || key === "potentially_unenforceable") {
    return "high";
  }
  if (key === "one_sided" || key === "slightly_unusual") {
    return "medium";
  }
  return "standard";
}

function parseDistribution(
  raw: RiskDistribution | Record<string, unknown> | string | null | undefined
): Record<string, unknown> {
  if (!raw) return {};
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  }
  return typeof raw === "object" ? (raw as Record<string, unknown>) : {};
}

/**
 * Derive consistent clause counts from live/loaded `clauses` when available,
 * falling back cleanly to summary `risk_distribution` without double-counting aliases.
 */
export function computeClauseCounts(
  clauses?: ClauseAnalysis[] | null,
  rawDistribution?: RiskDistribution | Record<string, unknown> | string | null
): ClauseCounts {
  if (clauses && clauses.length > 0) {
    let standard = 0;
    let slightlyUnusual = 0;
    let oneSided = 0;
    let highRisk = 0;
    let unenforceable = 0;

    for (const c of clauses) {
      const key = getDetailedRiskKey(c.risk_category);
      if (key === "standard") standard += 1;
      else if (key === "slightly_unusual") slightlyUnusual += 1;
      else if (key === "one_sided") oneSided += 1;
      else if (key === "high_risk") highRisk += 1;
      else unenforceable += 1;
    }

    const total = clauses.length;
    return {
      total,
      standard,
      slightlyUnusual,
      oneSided,
      highRisk,
      unenforceable,
      filterCounts: {
        all: total,
        high: highRisk + unenforceable,
        medium: slightlyUnusual + oneSided,
        standard,
      },
    };
  }

  const dist = parseDistribution(rawDistribution);
  // Backend emits both canonical names (standard, one_sided, high_risk, potentially_unenforceable)
  // and legacy/uppercase aliases (low, medium, high, critical) — take canonical OR alias, NEVER sum both.
  const standard = Number(dist.standard ?? dist.low ?? dist.LOW ?? 0) || 0;
  const slightlyUnusual = Number(dist.slightly_unusual ?? 0) || 0;
  const oneSided =
    slightlyUnusual > 0
      ? Number(dist.one_sided ?? 0) || 0
      : Number(dist.one_sided ?? dist.medium ?? dist.MEDIUM ?? 0) || 0;
  const highRisk = Number(dist.high_risk ?? dist.high ?? dist.HIGH ?? 0) || 0;
  const unenforceable =
    Number(dist.potentially_unenforceable ?? dist.critical ?? dist.CRITICAL ?? 0) || 0;

  let sum = standard + slightlyUnusual + oneSided + highRisk + unenforceable;

  // Fallback for category-object-only distributions (e.g. {"Liability": {"clause_count": 3}})
  let adjustedStandard = standard;
  if (sum === 0) {
    let categoryTotal = Number(dist.total_clauses || 0) || 0;
    if (categoryTotal === 0) {
      for (const val of Object.values(dist)) {
        if (val && typeof val === "object" && "clause_count" in val) {
          categoryTotal += Number((val as { clause_count?: number }).clause_count || 0);
        }
      }
    }
    if (categoryTotal > 0) {
      adjustedStandard = categoryTotal;
      sum = categoryTotal;
    }
  }

  return {
    total: sum,
    standard: adjustedStandard,
    slightlyUnusual,
    oneSided,
    highRisk,
    unenforceable,
    filterCounts: {
      all: sum,
      high: highRisk + unenforceable,
      medium: slightlyUnusual + oneSided,
      standard: adjustedStandard,
    },
  };
}
