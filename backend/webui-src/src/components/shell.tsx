import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  FolderKanban, BookText, Boxes, ShieldCheck, FileBox, MapPinned,
  PanelLeftClose, PanelLeft, Moon, Sun, LogOut,
} from 'lucide-react';
import { auth } from '@/lib/api';
import { applyTheme, initTheme, type Theme } from '@/lib/utils';
import { cn } from '@/lib/utils';

const NAV = [
  { to: '/', label: 'Proyek', icon: FolderKanban, end: true },
  { to: '/ahsp', label: 'AHSP', icon: BookText },
  { to: '/bahan-upah', label: 'Bahan & Upah', icon: Boxes },
  { to: '/harga', label: 'Cek Harga', icon: MapPinned },
  { to: '/admin', label: 'Admin', icon: ShieldCheck },
];

export function Shell() {
  const nav = useNavigate();
  const [collapsed, setCollapsed] = useState(localStorage.getItem('boq_sb') === '1');
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => { setTheme(initTheme()); }, []);
  const toggleTheme = () => { const t = theme === 'dark' ? 'light' : 'dark'; setTheme(t); applyTheme(t); };
  const toggleSb = () => { const c = !collapsed; setCollapsed(c); localStorage.setItem('boq_sb', c ? '1' : '0'); };

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <aside className={cn('shrink-0 border-r border-border bg-surface flex flex-col transition-all duration-200',
        collapsed ? 'w-16' : 'w-60')}>
        <div className="h-14 flex items-center gap-2 px-4 border-b border-border">
          <FileBox className="h-5 w-5 text-primary shrink-0" />
          {!collapsed && <span className="font-semibold tracking-tight">BOQ Generator</span>}
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) => cn(
                'flex items-center gap-3 rounded-lg px-3 h-10 text-sm transition-colors',
                collapsed && 'justify-center px-0',
                isActive ? 'bg-primary/10 text-primary font-medium' : 'text-muted hover:text-fg hover:bg-bg')}
              title={label}>
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <button onClick={toggleSb}
          className="h-11 flex items-center justify-center gap-2 border-t border-border text-muted hover:text-fg text-sm">
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <><PanelLeftClose className="h-4 w-4" /> Ciutkan</>}
        </button>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-14 shrink-0 border-b border-border bg-surface/80 backdrop-blur flex items-center justify-end gap-1 px-4">
          <button onClick={toggleTheme} className="btn-ghost h-9 w-9 p-0" title="Tema">
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <button onClick={() => { auth.clear(); nav('/login'); }} className="btn-ghost h-9 px-3" title="Keluar">
            <LogOut className="h-4 w-4" /> <span className="hidden sm:inline">Keluar</span>
          </button>
        </header>
        <main className="flex-1 min-h-0 flex flex-col p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
