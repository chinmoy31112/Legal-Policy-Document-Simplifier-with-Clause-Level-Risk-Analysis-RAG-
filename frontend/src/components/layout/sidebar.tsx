"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Shield, 
  Upload, 
  BookOpen, 
  Settings, 
  LayoutDashboard, 
  History, 
  FileText,
  Sparkles,
  UserCheck
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload Document', href: '/upload', icon: Upload },
  { name: 'My Documents', href: '/documents', icon: FileText },
  { name: 'Knowledge Base', href: '/dashboard/knowledge-base', icon: BookOpen },
  { name: 'History', href: '/dashboard/history', icon: History },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col bg-[#0b0f19] border-r border-slate-800/80 text-slate-200 select-none">
      {/* Brand Header */}
      <div className="flex h-20 shrink-0 items-center px-6 border-b border-slate-800/80 bg-[#0b0f19]/80 backdrop-blur-md">
        <div className="flex items-center gap-3 font-semibold text-lg tracking-tight font-heading">
          <div className="relative w-10 h-10 rounded-xl gradient-emerald flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white">
            <Shield className="h-5 w-5" />
            <Sparkles className="h-3 w-3 absolute -top-1 -right-1 text-emerald-300 animate-pulse" />
          </div>
          <div>
            <div className="font-extrabold text-base leading-tight tracking-tight text-white flex items-center gap-1.5">
              GovLegal <span className="gradient-text-emerald">AI</span>
            </div>
            <div className="text-[10px] font-bold tracking-widest text-emerald-400/90 uppercase">
              Policy Intelligence
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex flex-1 flex-col overflow-y-auto pt-5 pb-4 px-3">
        <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Core Navigation
        </div>
        <nav className="flex-1 space-y-1.5">
          {navigation.map((item) => {
            const isActive = 
              pathname === item.href || 
              (item.href !== '/dashboard' && pathname.startsWith(item.href));
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'group flex items-center rounded-xl px-3.5 py-3 text-sm font-medium transition-all duration-300 relative',
                  isActive
                    ? 'bg-gradient-to-r from-emerald-500/20 to-teal-500/10 text-emerald-400 border border-emerald-500/30 shadow-lg shadow-emerald-500/5'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent'
                )}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-emerald-400 rounded-r-full shadow-sm shadow-emerald-400/50" />
                )}
                <item.icon
                  className={cn(
                    'mr-3 h-5 w-5 flex-shrink-0 transition-all duration-300',
                    isActive 
                      ? 'text-emerald-400 scale-110 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]' 
                      : 'text-slate-400 group-hover:text-slate-200'
                  )}
                  aria-hidden="true"
                />
                <span className="truncate">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* System Settings & Officer Badge */}
        <div className="pt-4 mt-auto space-y-3">
          <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            System & Workspace
          </div>
          <Link
            href="/dashboard/settings"
            className={cn(
              'group flex items-center rounded-xl px-3.5 py-3 text-sm font-medium transition-all duration-300',
              pathname === '/dashboard/settings' || pathname === '/settings'
                ? 'bg-gradient-to-r from-emerald-500/20 to-teal-500/10 text-emerald-400 border border-emerald-500/30'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent'
            )}
          >
            <Settings className="mr-3 h-5 w-5 flex-shrink-0 text-slate-400 group-hover:text-slate-200" aria-hidden="true" />
            System Settings
          </Link>

          {/* Officer Verification Card */}
          <div className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800/90 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <UserCheck className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="text-xs font-bold text-slate-200 truncate">Legal Officer</div>
              <div className="text-[10px] text-emerald-400 font-semibold truncate flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping inline-block" />
                Active Session
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
