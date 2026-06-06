import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileBox } from 'lucide-react';
import { api } from '@/lib/api';
import { Button, Field } from '@/components/ui';

export default function Login() {
  const nav = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      if (mode === 'register') await api.register(email, password, fullName || undefined);
      await api.login(email, password);
      nav('/');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Gagal'); setBusy(false);
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-fg">
            <FileBox className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold">BOQ Generator</h1>
          <p className="text-sm text-muted">{mode === 'login' ? 'Masuk ke akun kamu' : 'Buat akun baru'}</p>
        </div>
        <div className="card p-6">
          <form onSubmit={submit} className="space-y-4">
            {mode === 'register' && (
              <Field label="Nama lengkap">
                <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Opsional" />
              </Field>
            )}
            <Field label="Email">
              <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@email.com" />
            </Field>
            <Field label="Password" hint={mode === 'register' ? 'Minimal 8 karakter' : undefined}>
              <input className="input" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </Field>
            {err && <div className="rounded-lg border border-danger/40 bg-danger/10 text-danger p-3 text-sm">{err}</div>}
            <Button type="submit" loading={busy} className="w-full">{mode === 'login' ? 'Masuk' : 'Daftar'}</Button>
          </form>
        </div>
        <p className="text-center text-sm text-muted">
          {mode === 'login' ? 'Belum punya akun? ' : 'Sudah punya akun? '}
          <button className="text-primary font-medium hover:underline"
            onClick={() => { setErr(null); setMode(mode === 'login' ? 'register' : 'login'); }}>
            {mode === 'login' ? 'Daftar' : 'Masuk'}
          </button>
        </p>
      </div>
    </div>
  );
}
