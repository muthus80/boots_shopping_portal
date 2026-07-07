import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';

// ── Mock the auth store ──────────────────────────────────────────────────────
const mockLogin = vi.fn();
const mockUseAuth = vi.fn(() => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: mockLogin,
  register: vi.fn(),
  logout: vi.fn(),
  setUser: vi.fn(),
  setAccessToken: vi.fn(),
}));

vi.mock('../stores/authStore', () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ── Mock react-router navigate ────────────────────────────────────────────────
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ── Helpers ───────────────────────────────────────────────────────────────────
const renderPage = () =>
  render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  );

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the login form with all required fields', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders a link to the registration page', () => {
    renderPage();

    const link = screen.getByRole('link', { name: /create one/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/register');
  });

  it('shows validation error when email is empty on submit', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/email address is required/i)).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid email format', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'not-an-email');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/valid email address/i)).toBeInTheDocument();
    });
  });

  it('shows validation error when password is empty on submit', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'user@example.com');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('calls login with correct credentials on valid submission', async () => {
    mockLogin.mockResolvedValueOnce(undefined);

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledOnce();
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'jane@example.com',
        password: 'Password1',
      });
    });
  });

  it('navigates to home on successful login', async () => {
    mockLogin.mockResolvedValueOnce(undefined);

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('displays a server error message for invalid credentials (401)', async () => {
    const axiosError = {
      isAxiosError: true,
      response: { status: 401, data: { detail: 'Invalid credentials' } },
    };

    const axiosMock = await import('axios');
    vi.spyOn(axiosMock.default, 'isAxiosError').mockReturnValueOnce(true);

    mockLogin.mockRejectedValueOnce(axiosError);

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'WrongPass1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
    });
  });

  it('displays a rate limit error message (429)', async () => {
    const axiosError = {
      isAxiosError: true,
      response: { status: 429, data: { detail: 'Rate limit exceeded' } },
    };

    const axiosMock = await import('axios');
    vi.spyOn(axiosMock.default, 'isAxiosError').mockReturnValueOnce(true);

    mockLogin.mockRejectedValueOnce(axiosError);

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/too many login attempts/i)).toBeInTheDocument();
    });
  });

  it('shows loading state while submitting', async () => {
    let resolve: (v: unknown) => void;
    const pending = new Promise((res) => {
      resolve = res;
    });
    mockLogin.mockReturnValueOnce(pending);

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    // Button should show loading text while pending
    expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();

    // Resolve to clean up
    resolve!(undefined);
  });

  it('fields have correct autocomplete attributes', () => {
    renderPage();

    expect(screen.getByLabelText(/email address/i)).toHaveAttribute('autocomplete', 'email');
    expect(screen.getByLabelText(/^password/i)).toHaveAttribute('autocomplete', 'current-password');
  });

  it('password input is of type password (not plain text)', () => {
    renderPage();

    expect(screen.getByLabelText(/^password/i)).toHaveAttribute('type', 'password');
  });

  it('does not navigate when login fails', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Login failed'));

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
