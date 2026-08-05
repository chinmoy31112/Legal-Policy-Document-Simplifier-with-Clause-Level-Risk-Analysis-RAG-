import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, Upload, BookOpen, Settings, LayoutDashboard, History } from 'lucide-react';

import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload Document', href: '/upload', icon: Upload },
  { name: 'My Documents', href: '/documents', icon: FileText },
  { name: 'Knowledge Base', href: '/knowledge-base', icon: BookOpen },
  { name: 'History', href: '/history', icon: History },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card text-card-foreground">
      <div className="flex h-16 shrink-0 items-center border-b px-6">
        <div className="flex items-center gap-2 font-bold text-lg text-primary">
          <FileText className="h-6 w-6" />
          <span>LegalSimplifier</span>
        </div>
      </div>
      <div className="flex flex-1 flex-col overflow-y-auto pt-6 pb-4">
        <nav className="flex-1 space-y-1 px-4">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors'
                )}
              >
                <item.icon
                  className={cn(
                    isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground',
                    'mr-3 h-5 w-5 flex-shrink-0 transition-colors'
                  )}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="border-t p-4">
        <Link
          href="/settings"
          className={cn(
            pathname === '/settings'
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors'
          )}
        >
          <Settings className="mr-3 h-5 w-5 flex-shrink-0" aria-hidden="true" />
          Settings
        </Link>
      </div>
    </div>
  );
}
