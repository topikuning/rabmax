'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { LayoutDashboard, FileBox, BookOpen, Boxes, LogOut, ShieldAlert } from 'lucide-react';
import { auth } from '@/lib/api';
import { cn } from '@/lib/utils';

const LINKS = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/ahsp', label: 'AHSP', icon: BookOpen },
  { href: '/bahan-upah', label: 'Bahan & Upah', icon: Boxes },
  { href: '/admin', label: 'Admin', icon: ShieldAlert },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState(false);

  useEffect(() => setAuthed(auth.isAuthed()), [pathname]);

  if (pathname === '/login') return null;

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <FileBox className="h-5 w-5 text-primary" />
          <span>BOQ Generator</span>
        </Link>

        {authed && (
          <nav className="flex items-center gap-1">
            {LINKS.map(({ href, label, icon: Icon }) => {
              const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    'flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors',
                    active
                      ? 'bg-accent text-accent-foreground font-medium'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/60',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
            <button
              onClick={() => {
                auth.logout();
                router.replace('/login');
              }}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              title="Keluar"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Keluar</span>
            </button>
          </nav>
        )}
      </div>
    </header>
  );
}
