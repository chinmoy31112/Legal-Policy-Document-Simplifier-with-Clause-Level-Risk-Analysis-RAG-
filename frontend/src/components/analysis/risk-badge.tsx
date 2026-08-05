import { cn } from '@/lib/utils';
import { AlertTriangle, Info, ShieldAlert, ShieldCheck, HelpCircle } from 'lucide-react';

export function RiskBadge({ category, score, className }: { category: string; score?: number; className?: string }) {
  let colorClass = '';
  let icon = null;
  let label = category.replace('_', ' ');

  switch (category) {
    case 'standard':
      colorClass = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-200 dark:border-green-800';
      icon = <ShieldCheck className="w-3 h-3 mr-1" />;
      break;
    case 'slightly_unusual':
      colorClass = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800';
      icon = <Info className="w-3 h-3 mr-1" />;
      break;
    case 'one_sided':
      colorClass = 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 border-orange-200 dark:border-orange-800';
      icon = <AlertTriangle className="w-3 h-3 mr-1" />;
      break;
    case 'high_risk':
      colorClass = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-200 dark:border-red-800';
      icon = <ShieldAlert className="w-3 h-3 mr-1" />;
      break;
    case 'potentially_unenforceable':
      colorClass = 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 border-purple-200 dark:border-purple-800';
      icon = <ShieldAlert className="w-3 h-3 mr-1" />;
      break;
    default:
      colorClass = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 border-gray-200 dark:border-gray-700';
      icon = <HelpCircle className="w-3 h-3 mr-1" />;
  }

  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize', colorClass, className)}>
      {icon}
      {label}
      {score !== undefined && <span className="ml-1 opacity-70 font-normal border-l pl-1 border-current ml-1">Score: {score}</span>}
    </span>
  );
}
