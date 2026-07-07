import React, { useState, FormEvent } from 'react';
import { useAuth } from '../stores/authStore';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Login failed. Please check your credentials and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Sign In</h1>
        <p style={styles.subtitle}>Welcome back! Please sign in to your account.</p>

        {error && (
          <div style={styles.errorBox} role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate style={styles.form}>
          <div style={styles.fieldGroup}>
            <label htmlFor="email" style={styles.label}>
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              disabled={loading}
              style={styles.input}
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="password" style={styles.label}>
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
              disabled={loading}
              style={styles.input}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !email || !password}
            style={{
              ...styles.button,
              ...(loading || !email || !password ? styles.buttonDisabled : {}),
            }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p style={styles.footerText}>
          Don&apos;t have an account?{' '}
          <a href="/register" style={styles.link}>
            Create one
          </a>
        </p>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
    padding: '1rem',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.1)',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '420px',
  },
  title: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.75rem',
    fontWeight: 700,
    color: '#1a1a1a',
    textAlign: 'center',
  },
  subtitle: {
    margin: '0 0 1.5rem 0',
    fontSize: '0.95rem',
    color: '#666666',
    textAlign: 'center',
  },
  errorBox: {
    backgroundColor: '#fff0f0',
    border: '1px solid #ffcccc',
    borderRadius: '4px',
    color: '#cc0000',
    fontSize: '0.875rem',
    marginBottom: '1.25rem',
    padding: '0.75rem 1rem',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.375rem',
  },
  label: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: '#333333',
  },
  input: {
    border: '1px solid #cccccc',
    borderRadius: '4px',
    fontSize: '1rem',
    padding: '0.625rem 0.75rem',
    outline: 'none',
    transition: 'border-color 0.2s',
    width: '100%',
    boxSizing: 'border-box',
  },
  button: {
    backgroundColor: '#1a73e8',
    border: 'none',
    borderRadius: '4px',
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: 600,
    marginTop: '0.5rem',
    padding: '0.75rem',
    transition: 'background-color 0.2s',
    width: '100%',
  },
  buttonDisabled: {
    backgroundColor: '#a0bce8',
    cursor: 'not-allowed',
  },
  footerText: {
    fontSize: '0.875rem',
    color: '#666666',
    marginTop: '1.5rem',
    textAlign: 'center',
  },
  link: {
    color: '#1a73e8',
    textDecoration: 'none',
    fontWeight: 600,
  },
};

export default LoginPage;