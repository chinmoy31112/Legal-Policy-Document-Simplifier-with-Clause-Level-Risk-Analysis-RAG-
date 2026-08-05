import { DocumentStatus } from '@/types/document';
import { cn } from '@/lib/utils';
import { Loader2, CheckCircle, Clock, AlertCircle, Search } from 'lucide-react';

export function StatusBadge({ status }: { status: string }) {
  let colorClass = '';
  let icon = null;
  let label = status;

  switch (status) {
    case DocumentStatus.UPLOADED:
      colorClass = 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      icon = <Clock className="w-3 h-3 mr-1" />;
      label = 'Uploaded';
      break;
    case DocumentStatus.EXTRACTING:
      colorClass = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      icon = <Search className="w-3 h-3 mr-1" />;
      label = 'Extracting Text';
      break;
    case DocumentStatus.SEGMENTING:
      colorClass = 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
      icon = <Loader2 className="w-3 h-3 mr-1 animate-spin" />;
      label = 'Segmenting Clauses';
      break;
    case DocumentStatus.ANALYZING:
      colorClass = 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
      icon = <Loader2 className="w-3 h-3 mr-1 animate-spin" />;
      label = 'Analyzing Risk';
      break;
    case DocumentStatus.COMPLETED:
      colorClass = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      icon = <CheckCircle className="w-3 h-3 mr-1" />;
      label = 'Completed';
      break;
    case DocumentStatus.FAILED:
      colorClass = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      icon = <AlertCircle className="w-3 h-3 mr-1" />;
      label = 'Failed';
      break;
    default:
      colorClass = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400';
  }

  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', colorClass)}>
      {icon}
      {label}
    </span>
  );
}
