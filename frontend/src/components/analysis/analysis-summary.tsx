import { DocumentAnalysis } from '@/types/analysis';
import { ShieldCheck, ShieldAlert, AlertTriangle, Info, Target, BarChart2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function AnalysisSummary({ analysis }: { analysis: DocumentAnalysis }) {
  
  // Calculate risk level color
  let riskColor = "text-green-500";
  let bgRiskColor = "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900";
  
  if (analysis.overall_risk_score > 75) {
    riskColor = "text-red-500";
    bgRiskColor = "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900";
  } else if (analysis.overall_risk_score > 40) {
    riskColor = "text-orange-500";
    bgRiskColor = "bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900";
  }

  // Parse risk distribution
  const distribution = typeof analysis.risk_distribution === 'string' 
    ? JSON.parse(analysis.risk_distribution) 
    : analysis.risk_distribution || {};

  return (
    <div className="space-y-6">
      {/* Overall Score Card */}
      <div className={cn("p-6 border rounded-xl flex items-start gap-6", bgRiskColor)}>
        <div className="flex-shrink-0 flex flex-col items-center justify-center bg-background border shadow-sm rounded-2xl w-24 h-24">
          <span className={cn("text-3xl font-bold", riskColor)}>{analysis.overall_risk_score}</span>
          <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mt-1">Risk Score</span>
        </div>
        
        <div className="flex-1 space-y-2">
          <h2 className="text-xl font-bold flex items-center">
            <Target className="w-5 h-5 mr-2 opacity-70" />
            Executive Summary
          </h2>
          <p className="text-sm leading-relaxed text-foreground/90">
            {analysis.overall_summary}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recommendations */}
        <div className="p-5 border rounded-xl bg-card shadow-sm">
          <h3 className="text-base font-semibold mb-4 flex items-center text-primary">
            <ShieldCheck className="w-5 h-5 mr-2" />
            Key Recommendations
          </h3>
          <ul className="space-y-3">
            {analysis.recommendations?.map((rec, i) => (
              <li key={i} className="flex items-start text-sm">
                <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 mr-3 text-xs font-bold">
                  {i + 1}
                </span>
                <span className="mt-0.5">{rec}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Risk Distribution Stats */}
        <div className="p-5 border rounded-xl bg-card shadow-sm">
          <h3 className="text-base font-semibold mb-4 flex items-center text-primary">
            <BarChart2 className="w-5 h-5 mr-2" />
            Clause Breakdown
          </h3>
          <div className="space-y-3">
            <DistributionRow 
              label="Standard" 
              count={distribution.standard || 0} 
              total={Object.values(distribution).reduce((a: any, b: any) => a + b, 0) as number}
              colorClass="bg-green-500" 
              icon={<ShieldCheck className="w-4 h-4 text-green-500" />} 
            />
            <DistributionRow 
              label="Slightly Unusual" 
              count={distribution.slightly_unusual || 0} 
              total={Object.values(distribution).reduce((a: any, b: any) => a + b, 0) as number}
              colorClass="bg-yellow-500" 
              icon={<Info className="w-4 h-4 text-yellow-500" />} 
            />
            <DistributionRow 
              label="One Sided" 
              count={distribution.one_sided || 0} 
              total={Object.values(distribution).reduce((a: any, b: any) => a + b, 0) as number}
              colorClass="bg-orange-500" 
              icon={<AlertTriangle className="w-4 h-4 text-orange-500" />} 
            />
            <DistributionRow 
              label="High Risk" 
              count={distribution.high_risk || 0} 
              total={Object.values(distribution).reduce((a: any, b: any) => a + b, 0) as number}
              colorClass="bg-red-500" 
              icon={<ShieldAlert className="w-4 h-4 text-red-500" />} 
            />
            <DistributionRow 
              label="Potentially Unenforceable" 
              count={distribution.potentially_unenforceable || 0} 
              total={Object.values(distribution).reduce((a: any, b: any) => a + b, 0) as number}
              colorClass="bg-purple-500" 
              icon={<ShieldAlert className="w-4 h-4 text-purple-500" />} 
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function DistributionRow({ label, count, total, colorClass, icon }: { label: string, count: number, total: number, colorClass: string, icon: React.ReactNode }) {
  if (count === 0) return null;
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
  
  return (
    <div className="flex items-center text-sm">
      <div className="w-40 flex items-center">
        {icon}
        <span className="ml-2 font-medium">{label}</span>
      </div>
      <div className="flex-1 mx-4 h-2 bg-muted rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full", colorClass)} style={{ width: `${percentage}%` }} />
      </div>
      <div className="w-12 text-right text-muted-foreground font-mono text-xs">
        {count}
      </div>
    </div>
  );
}
