import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'BOQ Generator',
  description: 'BOQ Generator untuk lelang pemerintah Indonesia',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="border-b">
            <div className="container mx-auto px-4 py-4 flex items-center justify-between">
              <h1 className="text-xl font-semibold">BOQ Generator</h1>
              <nav className="flex gap-4 text-sm">
                <a href="/" className="hover:text-primary">Dashboard</a>
                <a href="/projects" className="hover:text-primary">Projects</a>
                <a href="/ahsp" className="hover:text-primary">AHSP</a>
                <a href="/bahan-upah" className="hover:text-primary">Bahan & Upah</a>
              </nav>
            </div>
          </header>
          <main className="flex-1 container mx-auto px-4 py-6">{children}</main>
          <footer className="border-t mt-auto">
            <div className="container mx-auto px-4 py-4 text-sm text-muted-foreground">
              BOQ Generator v0.1.0 — Build per LKPP &amp; Permen PUPR 8/2023
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
