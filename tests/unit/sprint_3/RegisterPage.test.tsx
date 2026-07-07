import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { RegisterPage } from './RegisterPage';

// ── Mock the auth store ──────────────────────────────────────────────────────
const mockRegister = vi.fn();
const mockUseAuth = vi.fn(() => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: vi.fn(),
  register: mockRegister,
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
      <RegisterPage />
    </BrowserRouter>
  );

const fillForm = async (
  user: ReturnType<typeof userEvent.setup>,
  overrides: Partial<{
    fullName: string;
    email: string;
    password: string;
    confirmPassword: string;
  }> = {}
) => {
  const values = {
    fullName: 'Jane Doe',
    email: 'jane@example.com',
    password: 'Password1',
    confirmPassword: 'Password1',
    ...overrides,
  };

  if (values.fullName) {
    await user.type(screen.getByLabelText(/full name/i), values.fullName);
  }
  await user.type(screen.getByLabelText(/email address/i), values.email);
  await user.type(screen.getByLabelText(/^password/i), values.password);
  await user.type(screen.getByLabelText(/confirm password/i), values.confirmPassword);
};

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the registration form with all required fields', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('renders a link to the login page', () => {
    renderPage();

    const link = screen.getByRole('link', { name: /sign in/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/login');
  });

  it('shows validation error when email is empty on submit', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: /create account/i }));

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

  it('shows validation error when password is too short', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/^password/i), 'short');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('shows validation error when password fails complexity check', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/^password/i), 'alllowercase1');
    await user.tab();

    await waitFor(() => {
      // Use role="alert" to disambiguate from the hint text paragraph
      const alerts = screen.getAllByRole('alert');
      const complexityAlert = alerts.find((el) =>
        /uppercase.*lowercase.*number/i.test(el.textContent ?? '')
      );
      expect(complexityAlert).toBeInTheDocument();
    });
  });

  it('shows validation error when passwords do not match', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.type(screen.getByLabelText(/confirm password/i), 'Different1');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
  });

  it('calls authRegister with correct data on valid submission', async () => {
    mockRegister.mockResolvedValueOnce({
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 1800,
    });

    const user = userEvent.setup();
    renderPage();

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledOnce();
      expect(mockRegister).toHaveBeenCalledWith({
        email: 'jane@example.com',
        password: 'Password1',
        full_name: 'Jane Doe',
      });
    });
  });

  it('navigates to home on successful registration', async () => {
    mockRegister.mockResolvedValueOnce({
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 1800,
    });

    const user = userEvent.setup();
    renderPage();

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('does not include full_name when the field is empty', async () => {
    mockRegister.mockResolvedValueOnce({
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 1800,
    });

    const user = userEvent.setup();
    renderPage();

    // Skip fullName, only fill required fields
    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'Password1');
    await user.type(screen.getByLabelText(/confirm password/i), 'Password1');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        email: 'jane@example.com',
        password: 'Password1',
        full_name: undefined,
      });
    });
  });

  it('displays a server error when email is already registered (409)', async () => {
    const axiosError = {
      isAxiosError: true,
      response: { status: 409, data: { detail: 'Email already registered' } },
    };

    // Make axios.isAxiosError return true for this mock
    const axiosMock = await import('axios');
    vi.spyOn(axiosMock.default, 'isAxiosError').mockReturnValueOnce(true);

    mockRegister.mockRejectedValueOnce(axiosError);

    const user = userEvent.setup();
    renderPage();

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/email already exists/i)).toBeInTheDocument();
    });
  });

  it('shows loading state while submitting', async () => {
    let resolve: (v: unknown) => void;
    const pending = new Promise((res) => {
      resolve = res;
    });
    mockRegister.mockReturnValueOnce(pending);

    const user = userEvent.setup();
    renderPage();

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: /create account/i }));

    // Button should show loading text while pending
    expect(screen.getByRole('button', { name: /creating account/i })).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();

    // Resolve to clean up
    resolve!({ access_token: 'tok', token_type: 'bearer' });
  });

  it('fields have correct autocomplete attributes for accessibility', () => {
    renderPage();

    expect(screen.getByLabelText(/full name/i)).toHaveAttribute('autocomplete', 'name');
    expect(screen.getByLabelText(/email address/i)).toHaveAttribute('autocomplete', 'email');
    expect(screen.getByLabelText(/^password/i)).toHaveAttribute('autocomplete', 'new-password');
    expect(screen.getByLabelText(/confirm password/i)).toHaveAttribute('autocomplete', 'new-password');
  });

  it('password and confirm inputs are of type password (not plain text)', () => {
    renderPage();

    expect(screen.getByLabelText(/^password/i)).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText(/confirm password/i)).toHaveAttribute('type', 'password');
  });
});
