import type { Metadata } from 'next';
import './globals.css';
import { Nav } from '@/components/nav';

export const metadata: Metadata = {
  title: 'BOQ Generator',
  description: 'BOQ Generator untuk lelang pemerintah Indonesia (LKPP)',
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
          <Nav />
          <main className="flex-1 container mx-auto px-4 py-8 animate-fade-in">
            {children}
          </main>
          <footer className="border-t border-border mt-auto">
            <div className="container mx-auto px-4 py-4 text-xs text-muted-foreground">
              BOQ Generator — sesuai LKPP, Permen PUPR 8/2023 &amp; SE DJBK 47/2026
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
