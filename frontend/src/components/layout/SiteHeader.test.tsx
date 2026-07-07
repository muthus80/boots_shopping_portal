import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SiteHeader } from './SiteHeader';
import type { Category, User } from '../../types/index';

// ── Auth mock state type ──────────────────────────────────────────────────────

interface MockAuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: ReturnType<typeof vi.fn>;
  register: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  setUser: ReturnType<typeof vi.fn>;
  setAccessToken: ReturnType<typeof vi.fn>;
}

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockLogout = vi.fn();

const defaultAuthState: MockAuthState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: vi.fn(),
  register: vi.fn(),
  logout: mockLogout,
  setUser: vi.fn(),
  setAccessToken: vi.fn(),
};

// Use a plain object reference that tests can mutate
let currentAuthState: MockAuthState = defaultAuthState;

vi.mock('../../stores/authStore', () => ({
  useAuth: () => currentAuthState,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockGetCategories = vi.fn();
vi.mock('../../api/categories', () => ({
  getCategories: () => mockGetCategories(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ── Helpers ───────────────────────────────────────────────────────────────────

const MOCK_CATEGORIES: Category[] = [
  {
    id: '1',
    name: 'Ankle Boots',
    slug: 'ankle-boots',
    description: 'Stylish ankle boots',
    parent_id: null,
    image_url: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    name: 'Chelsea Boots',
    slug: 'chelsea-boots',
    description: 'Classic Chelsea boots',
    parent_id: null,
    image_url: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const renderHeader = (queryClient?: QueryClient) => {
  const qc = queryClient ?? createQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <SiteHeader />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('SiteHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCategories.mockResolvedValue(MOCK_CATEGORIES);
    currentAuthState = { ...defaultAuthState, logout: mockLogout };
  });

  // ── Structure ──────────────────────────────────────────────────────────────

  it('renders a <header> element with role banner', () => {
    renderHeader();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders the site logo link pointing to /', () => {
    renderHeader();
    const logo = screen.getByRole('link', { name: /boots shop.*homepage/i });
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveAttribute('href', '/');
  });

  it('renders a cart link', () => {
    renderHeader();
    const cartLink = screen.getByRole('link', { name: /shopping cart/i });
    expect(cartLink).toBeInTheDocument();
    expect(cartLink).toHaveAttribute('href', '/cart');
  });

  it('renders a search form', () => {
    renderHeader();
    expect(screen.getAllByRole('search')[0]).toBeInTheDocument();
  });

  // ── Unauthenticated state ──────────────────────────────────────────────────

  it('shows Sign In and Register links when user is not authenticated', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument();
  });

  it('does not show Log Out when user is not authenticated', () => {
    renderHeader();
    expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument();
  });

  // ── Authenticated state ────────────────────────────────────────────────────

  it('shows My Orders link and Log Out button when user is authenticated', () => {
    currentAuthState = {
      user: {
        id: 'u1',
        email: 'jane@example.com',
        full_name: 'Jane Doe',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      accessToken: 'token123',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: mockLogout,
      setUser: vi.fn(),
      setAccessToken: vi.fn(),
    };

    renderHeader();

    expect(screen.getByRole('link', { name: /my orders/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /sign in/i })).not.toBeInTheDocument();
  });

  it('calls logout when Log Out button is clicked', async () => {
    currentAuthState = {
      user: {
        id: 'u1',
        email: 'jane@example.com',
        full_name: 'Jane Doe',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      accessToken: 'token123',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: mockLogout,
      setUser: vi.fn(),
      setAccessToken: vi.fn(),
    };
    mockLogout.mockResolvedValueOnce(undefined);

    const user = userEvent.setup();
    renderHeader();

    await user.click(screen.getByRole('button', { name: /log out/i }));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledOnce();
    });
  });

  // ── Categories ─────────────────────────────────────────────────────────────

  it('renders category links after they load', async () => {
    renderHeader();

    await waitFor(() => {
      expect(screen.getAllByRole('link', { name: /ankle boots/i })[0]).toBeInTheDocument();
      expect(screen.getAllByRole('link', { name: /chelsea boots/i })[0]).toBeInTheDocument();
    });
  });

  it('category links point to /products?category=<slug>', async () => {
    renderHeader();

    await waitFor(() => {
      const ankleLinks = screen.getAllByRole('link', { name: /ankle boots/i });
      expect(ankleLinks[0]).toHaveAttribute('href', '/products?category=ankle-boots');
    });
  });

  it('shows a fallback Shop All link when categories fail to load', async () => {
    mockGetCategories.mockRejectedValueOnce(new Error('Network error'));

    renderHeader();

    await waitFor(() => {
      expect(screen.getAllByRole('link', { name: /shop all/i })[0]).toBeInTheDocument();
    });
  });

  // ── Mobile menu ────────────────────────────────────────────────────────────

  it('mobile menu is closed by default', () => {
    renderHeader();
    expect(screen.queryByRole('navigation', { name: /mobile navigation/i })).not.toBeInTheDocument();
  });

  it('opens mobile menu when toggle button is clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    const toggle = screen.getByRole('button', { name: /open navigation menu/i });
    await user.click(toggle);

    expect(screen.getByRole('navigation', { name: /mobile navigation/i })).toBeInTheDocument();
  });

  it('closes mobile menu when toggle is clicked a second time', async () => {
    const user = userEvent.setup();
    renderHeader();

    const toggle = screen.getByRole('button', { name: /open navigation menu/i });
    await user.click(toggle);
    await user.click(screen.getByRole('button', { name: /close navigation menu/i }));

    expect(screen.queryByRole('navigation', { name: /mobile navigation/i })).not.toBeInTheDocument();
  });

  // ── Search ─────────────────────────────────────────────────────────────────

  it('navigates to /products?search=<query> when search is submitted', async () => {
    const user = userEvent.setup();
    renderHeader();

    const searchInput = screen.getAllByRole('searchbox')[0];
    await user.type(searchInput, 'leather boots');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/products?search=leather%20boots');
    });
  });

  it('does not navigate when search query is empty', async () => {
    const user = userEvent.setup();
    renderHeader();

    const submitBtn = screen.getAllByRole('button', { name: /submit search/i })[0];
    await user.click(submitBtn);

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // ── Accessibility ──────────────────────────────────────────────────────────

  it('mobile menu toggle has correct aria-expanded attribute', async () => {
    const user = userEvent.setup();
    renderHeader();

    const toggle = screen.getByRole('button', { name: /open navigation menu/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggle);
    expect(screen.getByRole('button', { name: /close navigation menu/i })).toHaveAttribute(
      'aria-expanded',
      'true'
    );
  });

  it('search input has an accessible label', () => {
    renderHeader();
    expect(screen.getAllByLabelText(/search products/i)[0]).toBeInTheDocument();
  });

  it('cart link has an accessible aria-label', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: /shopping cart/i })).toBeInTheDocument();
  });
});
