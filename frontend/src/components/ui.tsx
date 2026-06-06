'use client';

import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// === Button ===
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'danger';
  size?: 'sm' | 'md';
  loading?: boolean;
};

const VARIANTS: Record<string, string> = {
  primary:
    'bg-primary text-primary-foreground hover:opacity-90 shadow-sm shadow-primary/20',
  secondary: 'bg-muted text-foreground hover:bg-muted/70',
  outline: 'border border-border bg-card hover:bg-muted/50',
  ghost: 'hover:bg-muted/60',
  danger: 'bg-destructive text-white hover:opacity-90',
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'disabled:opacity-50 disabled:pointer-events-none',
        size === 'sm' ? 'h-8 px-3 text-xs' : 'h-10 px-4 text-sm',
        VARIANTS[variant],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

// === Card ===
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('card-surface', className)} {...props} />;
}

// === Badge ===
export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: 'neutral' | 'primary' | 'success' | 'warning' | 'danger';
  className?: string;
  children: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    neutral: 'bg-muted text-muted-foreground',
    primary: 'bg-accent text-accent-foreground',
    success: 'bg-success/15 text-success',
    warning: 'bg-warning/15 text-warning',
    danger: 'bg-destructive/15 text-destructive',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

// === Status & mode helpers ===
const STATUS_TONE: Record<string, 'neutral' | 'primary' | 'success' | 'warning' | 'danger'> = {
  draft: 'neutral',
  parsing: 'warning',
  matching: 'warning',
  building: 'warning',
  ready_for_review: 'primary',
  finalized: 'success',
  failed: 'danger',
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? 'neutral'}>{status.replace(/_/g, ' ')}</Badge>;
}

export function ModeBadge({ mode }: { mode: string }) {
  return (
    <Badge tone="neutral">
      {mode === 'generate' ? 'Generate BOQ' : 'Analisa Profit'}
    </Badge>
  );
}

// === Inputs ===
export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        'w-full h-10 rounded-lg border border-border bg-card px-3 text-sm',
        'placeholder:text-muted-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        props.className,
      )}
    />
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
    </label>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-4 w-4 animate-spin', className)} />;
}

export function EmptyState({
  title,
  desc,
  action,
}: {
  title: string;
  desc?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="border border-dashed border-border rounded-2xl p-12 text-center">
      <p className="font-medium">{title}</p>
      {desc && <p className="text-sm text-muted-foreground mt-1">{desc}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
