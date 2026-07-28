import React from 'react';
import { ErrorSummary } from './ErrorSummary';

interface GlobalErrorBoundaryState {
  error: Error | null;
}

export class GlobalErrorBoundary extends React.Component<React.PropsWithChildren, GlobalErrorBoundaryState> {
  state: GlobalErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): GlobalErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Erro inesperado na interface do Portal Vesper:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
          <div style={{ maxWidth: 560, width: '100%' }}>
            <ErrorSummary
              title="Algo saiu do esperado"
              error="A tela encontrou um problema inesperado. Seus dados nao foram enviados novamente."
              onRetry={() => this.setState({ error: null })}
            />
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}

export default GlobalErrorBoundary;
