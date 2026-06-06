import {
  createContext, useContext, useState, useCallback, type ReactNode, type ButtonHTMLAttributes,
} from 'react';
import { Loader2, X, CheckCircle2, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

// ---- Button ----
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'ghost';
  loading?: boolean;
};
export function Button({ variant = 'primary', loading, className, children, disabled, ...p }: BtnProps) {
  const v = variant === 'primary' ? 'btn-primary' : variant === 'outline' ? 'btn-outline' : 'btn-ghost';
  return (
    <button className={cn(v, className)} disabled={disabled || loading} {...p}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-4 w-4 animate-spin', className)} />;
}

// ---- Modal ----
export function Modal({ open, onClose, title, children, footer, width = 460 }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; width?: number;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="card w-full animate-[fadein_.15s_ease]" style={{ maxWidth: width }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={onClose} className="text-muted hover:text-fg"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5">{children}</div>
        {footer && <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted">{hint}</span>}
    </label>
  );
}

const CHIP_TONE: Record<string, string> = {
  draft: 'bg-muted/15 text-muted',
  parsing: 'bg-warning/15 text-warning', matching: 'bg-warning/15 text-warning', building: 'bg-warning/15 text-warning',
  ready_for_review: 'bg-primary/15 text-primary', finalized: 'bg-success/15 text-success', failed: 'bg-danger/15 text-danger',
};
export function StatusChip({ status }: { status: string }) {
  return <span className={cn('chip', CHIP_TONE[status] || 'bg-muted/15 text-muted')}>{status.replace(/_/g, ' ')}</span>;
}

// ---- Toast ----
type Toast = { id: number; msg: string; ok: boolean };
const ToastCtx = createContext<(msg: string, ok?: boolean) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((msg: string, ok = true) => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, msg, ok }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 4000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] space-y-2 w-80">
        {items.map((t) => (
          <div key={t.id} className={cn('card p-3 flex items-start gap-2 text-sm shadow-lg',
            t.ok ? 'border-success/40' : 'border-danger/40')}>
            {t.ok ? <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  : <AlertTriangle className="h-4 w-4 text-danger mt-0.5 shrink-0" />}
            <span className="break-words">{t.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
