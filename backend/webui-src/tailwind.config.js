/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'hsl(var(--bg))',
        surface: 'hsl(var(--surface))',
        elevated: 'hsl(var(--elevated))',
        border: 'hsl(var(--border))',
        fg: 'hsl(var(--fg))',
        muted: 'hsl(var(--muted))',
        primary: 'hsl(var(--primary))',
        'primary-fg': 'hsl(var(--primary-fg))',
        success: 'hsl(var(--success))',
        warning: 'hsl(var(--warning))',
        danger: 'hsl(var(--danger))',
      },
      borderRadius: { xl: '0.9rem' },
    },
  },
  plugins: [],
};
