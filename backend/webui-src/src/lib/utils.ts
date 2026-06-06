import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function rupiah(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return '-';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(n);
}

export function num(n: number | null | undefined): string {
  if (n === null || n === undefined) return '-';
  return new Intl.NumberFormat('id-ID').format(n);
}

export type Theme = 'light' | 'dark';

export function initTheme(): Theme {
  const saved = (localStorage.getItem('boq_theme') as Theme) || 'light';
  applyTheme(saved);
  return saved;
}

export function applyTheme(t: Theme) {
  document.documentElement.classList.toggle('dark', t === 'dark');
  localStorage.setItem('boq_theme', t);
}
