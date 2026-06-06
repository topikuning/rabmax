import { Component, type ReactNode } from 'react';

interface State { error: Error | null }

// Tangkap error render → tampilkan pesan (jangan biarkan halaman blank).
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error) { console.error('BOQ render error:', error); }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'ui-monospace, monospace', color: '#b91c1c' }}>
          <h2 style={{ marginBottom: 8 }}>Terjadi error pada UI</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
            {this.state.error.message}
            {'\n\n'}
            {this.state.error.stack}
          </pre>
          <button onClick={() => location.reload()} style={{ marginTop: 12, padding: '6px 12px' }}>
            Muat ulang
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
