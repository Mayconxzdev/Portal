import React, { useState } from 'react';
import { LockKeyhole, LogIn, ShieldCheck, UserRound, Wifi, WifiOff } from 'lucide-react';
import { KodaMascot } from '../components/ui/KodaMascot';
import { readApiError } from '../lib/apiErrors';

interface LoginPageProps {
  onLoginSuccess: (userData: any) => void;
  apiStatus: 'online' | 'offline' | 'loading';
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess, apiStatus }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiLabel = apiStatus === 'online' ? 'API online' : apiStatus === 'offline' ? 'API offline' : 'Verificando API';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Preencha usuário e senha para entrar.');
      return;
    }

    if (apiStatus === 'offline') {
      setError('A API está offline. Inicie o Portal antes de tentar entrar.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = response.ok ? await response.json().catch(() => null) : null;
      if (!response.ok) {
        const apiError = await readApiError(response, 'Nao foi possivel entrar no Portal agora.');
        throw new Error(apiError.message || 'Usuario ou senha invalidos.');
      }

      if (data?.status === 'success' && data.user) {
        onLoginSuccess(data.user);
        return;
      }

      throw new Error('Resposta de login inválida.');
    } catch (err: any) {
      setError(err.message || 'Não foi possível conectar ao servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-brand-panel" aria-label="Portal Vesper">
        <div className="login-brand-copy">
          <span className="login-eyebrow"><ShieldCheck size={15} /> Portal Vesper</span>
          <h1>Central interna da operação Vesper</h1>
          <p>Entre para acessar Kanban, TI, Chat, Aprovações e Administração com dados reais do ambiente local.</p>
        </div>
        <div className="login-koda-wrap">
          <KodaMascot variant="security" size="xl" decorative={false} alt="Koda, assistente visual do Portal Vesper" withGlow />
        </div>
      </section>

      <section className="login-card glass-card" aria-label="Login">
        <div className="login-card-header">
          <div className="login-logo">V</div>
          <div>
            <h2>Entrar no Portal</h2>
            <p>Use sua conta corporativa de desenvolvimento.</p>
          </div>
        </div>

        <div className={`login-api-status login-api-status--${apiStatus}`}>
          {apiStatus === 'offline' ? <WifiOff size={16} /> : <Wifi size={16} />}
          <span>{apiLabel}</span>
        </div>

        {error && <div className="login-error" role="alert">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <label className="login-field" htmlFor="username">
            <span>Usuário</span>
            <div className="login-input-wrap">
              <UserRound size={17} />
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="vesper_admin"
                disabled={loading}
                autoComplete="username"
              />
            </div>
          </label>

          <label className="login-field" htmlFor="password">
            <span>Senha</span>
            <div className="login-input-wrap">
              <LockKeyhole size={17} />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Digite sua senha"
                disabled={loading}
                autoComplete="current-password"
              />
            </div>
          </label>

          <button className="login-submit" type="submit" disabled={loading || apiStatus === 'offline'}>
            {loading ? 'Entrando...' : 'Entrar'}
            <LogIn size={17} />
          </button>
        </form>

        <footer className="login-footer">
          <span>Ambiente local seguro</span>
          <span>Sem integrações externas nesta fase</span>
        </footer>
      </section>
    </main>
  );
};

export default LoginPage;
