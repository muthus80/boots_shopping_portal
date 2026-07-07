import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../stores/authStore';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || undefined,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        const message =
          data?.detail ||
          (Array.isArray(data?.detail)
            ? data.detail.map((d: { msg: string }) => d.msg).join(', ')
            : 'Registration failed. Please try again.');
        setError(typeof message === 'string' ? message : JSON.stringify(message));
        return;
      }

      const loginResponse = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ username: email, password }),
      });

      if (!loginResponse.ok) {
        navigate('/login');
        return;
      }

      const tokenData = await loginResponse.json();
      const accessToken: string = tokenData.access_token;

      const profileResponse = await fetch('/api/v1/account/me', {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!profileResponse.ok) {
        navigate('/login');
        return;
      }

      const userData = await profileResponse.json();
      login(userData, accessToken);
      navigate('/');
    } catch {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Create Account</h1>
        <p style={styles.subtitle}>Join us and start shopping for boots!</p>

        {error && (
          <div style={styles.errorBox} role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate style={styles.form}>
          <div style={styles.fieldGroup}>
            <label htmlFor="fullName" style={styles.label}>
              Full Name <span style={styles.optional}>(optional)</span>
            </label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Doe"
              style={styles.input}
              autoComplete="name"
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="email" style={styles.label}>
              Email Address <span style={styles.required}>*</span>
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              style={styles.input}
              autoComplete="email"
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="password" style={styles.label}>
              Password <span style={styles.required}>*</span>
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              style={styles.input}
              autoComplete="new-password"
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="confirmPassword" style={styles.label}>
              Confirm Password <span style={styles.required}>*</span>
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat your password"
              required
              style={styles.input}
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              ...styles.submitButton,
              ...(isLoading ? styles.submitButtonDisabled : {}),
            }}
          >
            {isLoading ? 'Creating Account…' : 'Create Account'}
          </button>
        </form>

        <p style={styles.loginPrompt}>
          Already have an account?{' '}
          <Link to="/login" style={styles.loginLink}>
            Sign in
          </Link>
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
    padding: '24px 16px',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
    padding: '40px 36px',
    width: '100%',
    maxWidth: '440px',
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    fontWeight: 700,
    color: '#1a1a1a',
    textAlign: 'center',
  },
  subtitle: {
    margin: '0 0 28px 0',
    fontSize: '15px',
    color: '#666666',
    textAlign: 'center',
  },
  errorBox: {
    backgroundColor: '#fff0f0',
    border: '1px solid #ffcccc',
    borderRadius: '8px',
    color: '#cc0000',
    fontSize: '14px',
    padding: '12px 16px',
    marginBottom: '20px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#333333',
  },
  optional: {
    fontWeight: 400,
    color: '#999999',
    fontSize: '13px',
  },
  required: {
    color: '#cc0000',
  },
  input: {
    border: '1px solid #dddddd',
    borderRadius: '8px',
    fontSize: '15px',
    padding: '10px 14px',
    outline: 'none',
    transition: 'border-color 0.2s',
    width: '100%',
    boxSizing: 'border-box',
  },
  submitButton: {
    backgroundColor: '#2c2c2c',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 600,
    marginTop: '8px',
    padding: '13px',
    transition: 'background-color 0.2s',
    width: '100%',
  },
  submitButtonDisabled: {
    backgroundColor: '#888888',
    cursor: 'not-allowed',
  },
  loginPrompt: {
    marginTop: '24px',
    textAlign: 'center',
    fontSize: '14px',
    color: '#555555',
  },
  loginLink: {
    color: '#2c2c2c',
    fontWeight: 600,
    textDecoration: 'underline',
  },
};

export { RegisterPage };
export default RegisterPage;