'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileBox } from 'lucide-react';
import { auth } from '@/lib/api';
import { Button, Card, Field, Input } from '@/components/ui';
import { cn } from '@/lib/utils';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === 'register') await auth.register(email, password, fullName || undefined);
      await auth.login(email, password);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal');
      setBusy(false);
    }
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
            <FileBox className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold">BOQ Generator</h1>
          <p className="text-sm text-muted-foreground">
            {mode === 'login' ? 'Masuk ke akun kamu' : 'Buat akun baru'}
          </p>
        </div>

        <Card className="p-6">
          <form onSubmit={submit} className="space-y-4">
            {mode === 'register' && (
              <Field label="Nama lengkap">
                <Input
                  placeholder="Opsional"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </Field>
            )}
            <Field label="Email">
              <Input
                type="email"
                required
                placeholder="nama@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Field label="Password" hint={mode === 'register' ? 'Minimal 8 karakter' : undefined}>
              <Input
                type="password"
                required
                minLength={8}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>

            {error && (
              <div className="rounded-lg border border-destructive/40 bg-destructive/10 text-destructive p-3 text-sm">
                {error}
              </div>
            )}

            <Button type="submit" loading={busy} className="w-full">
              {mode === 'login' ? 'Masuk' : 'Daftar'}
            </Button>
          </form>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          {mode === 'login' ? 'Belum punya akun? ' : 'Sudah punya akun? '}
          <button
            className={cn('text-primary font-medium hover:underline')}
            onClick={() => {
              setError(null);
              setMode(mode === 'login' ? 'register' : 'login');
            }}
          >
            {mode === 'login' ? 'Daftar' : 'Masuk'}
          </button>
        </p>
      </div>
    </div>
  );
}
