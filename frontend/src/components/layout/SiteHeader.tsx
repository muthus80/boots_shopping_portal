import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../stores/authStore';
import { getCategories } from '../../api/categories';
import type { Category } from '../../types/index';

// ── Mobile-menu toggle icon ──────────────────────────────────────────────────

const MenuIcon: React.FC<{ open: boolean }> = ({ open }) =>
  open ? (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ) : (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );

// ── Cart icon ────────────────────────────────────────────────────────────────

const CartIcon: React.FC = () => (
  <svg
    className="h-5 w-5"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
    />
  </svg>
);

// ── User icon ────────────────────────────────────────────────────────────────

const UserIcon: React.FC = () => (
  <svg
    className="h-5 w-5"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
    />
  </svg>
);

// ── Search icon ──────────────────────────────────────────────────────────────

const SearchIcon: React.FC = () => (
  <svg
    className="h-5 w-5"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
    />
  </svg>
);

// ── Search bar ───────────────────────────────────────────────────────────────

const SearchBar: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState<string>('');

  const handleSearch = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      navigate(`/products?search=${encodeURIComponent(trimmed)}`);
      setQuery('');
    }
  };

  return (
    <form
      role="search"
      onSubmit={handleSearch}
      className="relative flex items-center"
      aria-label="Search products"
    >
      <label htmlFor="site-search" className="sr-only">
        Search products
      </label>
      <input
        id="site-search"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search boots…"
        aria-label="Search products"
        className="w-48 rounded-lg border border-gray-300 bg-gray-50 py-1.5 pl-3 pr-9 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
      />
      <button
        type="submit"
        aria-label="Submit search"
        className="absolute right-2 text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
      >
        <SearchIcon />
      </button>
    </form>
  );
};

// ── Category links (fetched from API) ────────────────────────────────────────

interface CategoryNavProps {
  onLinkClick?: () => void;
}

const CategoryNav: React.FC<CategoryNavProps> = ({ onLinkClick }) => {
  const { data: categories, isLoading, isError } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 1000 * 60 * 10, // 10 minutes — categories rarely change
  });

  if (isLoading) {
    return (
      <li className="flex items-center gap-1 text-sm text-gray-400" aria-busy="true" aria-live="polite">
        <span className="sr-only">Loading categories</span>
        <span className="h-2 w-2 rounded-full bg-gray-300 animate-pulse" />
        <span className="h-2 w-16 rounded bg-gray-200 animate-pulse" />
      </li>
    );
  }

  if (isError || !categories || categories.length === 0) {
    // Graceful fallback — show a general shop link so navigation stays functional
    return (
      <li>
        <Link
          to="/products"
          onClick={onLinkClick}
          className="text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
        >
          Shop All
        </Link>
      </li>
    );
  }

  return (
    <>
      {categories.map((cat) => (
        <li key={cat.id}>
          <Link
            to={`/products?category=${cat.slug}`}
            onClick={onLinkClick}
            className="text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
          >
            {cat.name}
          </Link>
        </li>
      ))}
    </>
  );
};

// ── Account actions ──────────────────────────────────────────────────────────

interface AccountActionsProps {
  onLinkClick?: () => void;
}

const AccountActions: React.FC<AccountActionsProps> = ({ onLinkClick }) => {
  const { user, logout } = useAuth();

  const handleLogout = async (): Promise<void> => {
    await logout();
    onLinkClick?.();
  };

  if (user) {
    return (
      <>
        <Link
          to="/orders"
          onClick={onLinkClick}
          aria-label="View my orders"
          className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
        >
          <UserIcon />
          <span className="hidden lg:inline">My Orders</span>
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Log out"
          className="text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
        >
          Log Out
        </button>
      </>
    );
  }

  return (
    <>
      <Link
        to="/login"
        onClick={onLinkClick}
        aria-label="Sign in to your account"
        className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
      >
        <UserIcon />
        <span className="hidden lg:inline">Sign In</span>
      </Link>
      <Link
        to="/register"
        onClick={onLinkClick}
        className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1 transition-colors"
      >
        Register
      </Link>
    </>
  );
};

// ── SiteHeader ───────────────────────────────────────────────────────────────

export const SiteHeader: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const closeMobileMenu = (): void => setMobileMenuOpen(false);

  return (
    <header className="sticky top-0 z-50 bg-white shadow-sm" role="banner">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">

          {/* Logo / Home link */}
          <Link
            to="/"
            aria-label="Boots Shop — go to homepage"
            className="flex items-center gap-2 shrink-0 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded"
          >
            <span className="text-2xl" role="img" aria-hidden="true">👢</span>
            <span className="text-lg font-bold tracking-tight text-gray-900 hidden sm:inline">
              Boots Shop
            </span>
          </Link>

          {/* Desktop nav — categories */}
          <nav
            aria-label="Product categories"
            className="hidden md:flex items-center"
          >
            <ul className="flex items-center gap-5 list-none p-0 m-0">
              <CategoryNav />
            </ul>
          </nav>

          {/* Right side actions */}
          <div className="flex items-center gap-3">
            {/* Search — hidden on very small screens, visible from sm */}
            <div className="hidden sm:block">
              <SearchBar />
            </div>

            {/* Cart */}
            <Link
              to="/cart"
              aria-label="Shopping cart"
              className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
            >
              <CartIcon />
              <span className="hidden lg:inline">Cart</span>
            </Link>

            {/* Account (desktop) */}
            <div className="hidden sm:flex items-center gap-3">
              <AccountActions />
            </div>

            {/* Mobile menu toggle */}
            <button
              type="button"
              aria-controls="mobile-menu"
              aria-expanded={mobileMenuOpen}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="md:hidden p-1 rounded text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
            >
              <MenuIcon open={mobileMenuOpen} />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div
          id="mobile-menu"
          role="navigation"
          aria-label="Mobile navigation"
          className="md:hidden border-t border-gray-200 bg-white px-4 pb-4 pt-2"
        >
          {/* Mobile search */}
          <div className="mb-3 sm:hidden">
            <SearchBar />
          </div>

          {/* Mobile category links */}
          <nav aria-label="Product categories — mobile">
            <ul className="flex flex-col gap-2 list-none p-0 m-0 mb-3">
              <CategoryNav onLinkClick={closeMobileMenu} />
            </ul>
          </nav>

          {/* Mobile account actions */}
          <div className="flex flex-col gap-2 border-t border-gray-100 pt-3">
            <AccountActions onLinkClick={closeMobileMenu} />
          </div>
        </div>
      )}
    </header>
  );
};

export default SiteHeader;
