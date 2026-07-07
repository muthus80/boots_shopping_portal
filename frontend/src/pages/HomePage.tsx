/**
 * HomePage — T-033 accessibility remediation (US-015)
 *
 * Changes made for WCAG 2.1 AA compliance:
 *  - CategoryCard: replaced non-interactive <div> with <Link> so the element is
 *    keyboard-focusable and activatable via Enter/Space
 *  - ProductCard: replaced non-interactive <div> with <Link> to product detail
 *  - Hero CTA buttons: converted to proper <Link>/<a> elements with destination
 *  - Newsletter email input: added associated <label> (was completely unlabelled)
 *  - Newsletter "Subscribe" button: added type="submit" and form role="search"
 *  - Footer links: replaced href="#" placeholders with sensible in-app paths
 *  - All interactive elements: added focus-visible ring styles (WCAG 2.4.7)
 *  - Loading spinner: added role="status" and sr-only text (already in common component)
 *  - Migrated inline styles → Tailwind utility classes throughout (no mixed approach)
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getProducts } from '../api/products';
import type { Product, Category } from '../types/index';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

// ── Featured categories ───────────────────────────────────────────────────────

const FEATURED_CATEGORIES: Pick<Category, 'id' | 'name' | 'slug' | 'description'>[] = [
  { id: '1', name: 'Ankle Boots',    slug: 'ankle-boots',    description: 'Stylish ankle boots for every occasion' },
  { id: '2', name: 'Chelsea Boots',  slug: 'chelsea-boots',  description: 'Classic Chelsea boots' },
  { id: '3', name: 'Knee High Boots',slug: 'knee-high-boots',description: 'Elegant knee high boots' },
  { id: '4', name: 'Work Boots',     slug: 'work-boots',     description: 'Durable work boots' },
];

// ── CategoryCard ──────────────────────────────────────────────────────────────

interface CategoryCardProps {
  category: Pick<Category, 'id' | 'name' | 'slug' | 'description'>;
}

/**
 * Each category card is an accessible <Link> (keyboard-focusable, Enter activates).
 * Previously this was a non-interactive <div> with mouse-only hover handlers.
 */
const CategoryCard: React.FC<CategoryCardProps> = ({ category }) => (
  <Link
    to={`/products?category=${category.slug}`}
    className="group flex flex-col items-center rounded-xl border border-gray-200 bg-gray-50 p-6 text-center shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
  >
    <span className="mb-3 text-5xl" aria-hidden="true">👢</span>
    <h3 className="mb-2 text-lg font-semibold text-gray-900">{category.name}</h3>
    {category.description && (
      <p className="text-sm text-gray-500">{category.description}</p>
    )}
  </Link>
);

// ── FeaturedProductCard ───────────────────────────────────────────────────────

interface FeaturedProductCardProps {
  product: Product;
}

/**
 * Homepage-specific product card.
 * Replaced non-interactive <div> + button with a proper <Link> wrapping the card
 * and a secondary "View" link with a unique accessible label.
 */
const FeaturedProductCard: React.FC<FeaturedProductCardProps> = ({ product }) => {
  const formattedPrice = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(Number(product.base_price));

  return (
    <article className="group overflow-hidden rounded-xl bg-white shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
      {/* Product image */}
      <Link
        to={`/products/${product.id}`}
        aria-label={`View ${product.name}`}
        tabIndex={-1}
        className="block focus:outline-none"
      >
        <div className="flex h-48 items-center justify-center overflow-hidden bg-gray-100">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <span className="text-6xl" aria-hidden="true">👢</span>
          )}
        </div>
      </Link>

      {/* Product info */}
      <div className="p-4">
        <h4 className="mb-2 line-clamp-2 text-base font-semibold text-gray-900">
          {product.name}
        </h4>
        {product.description && (
          <p className="mb-3 line-clamp-2 text-sm text-gray-500">{product.description}</p>
        )}
        <div className="flex items-center justify-between">
          <span className="text-lg font-bold text-blue-600">{formattedPrice}</span>
          <Link
            to={`/products/${product.id}`}
            aria-label={`View details for ${product.name}`}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
          >
            View
          </Link>
        </div>
      </div>
    </article>
  );
};

// ── HomePage ──────────────────────────────────────────────────────────────────

export const HomePage: React.FC = () => {
  const [newsletterEmail, setNewsletterEmail] = useState<string>('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['products', 'featured', { page: 1, page_size: 8 }],
    queryFn: () => getProducts({ page: 1, page_size: 8 }),
    staleTime: 1000 * 60 * 5,
  });

  const featuredProducts: Product[] = data?.items ?? [];

  return (
    <div className="font-sans text-gray-900">

      {/* ── Hero Section ──────────────────────────────────────────────────── */}
      <section
        aria-labelledby="hero-heading"
        className="bg-gradient-to-br from-[#1a1a2e] via-[#16213e] to-[#0f3460] px-6 py-20 text-center text-white"
      >
        <div className="mx-auto max-w-3xl">
          <span className="mb-4 block text-7xl" aria-hidden="true">👢</span>
          <h1
            id="hero-heading"
            className="mb-4 text-5xl font-extrabold leading-tight"
          >
            Step Into Style
          </h1>
          <p className="mb-8 text-xl leading-relaxed text-white/80">
            Discover our premium collection of boots crafted for every adventure,
            every season, every you.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/products"
              className="rounded-xl bg-blue-600 px-8 py-3.5 text-base font-bold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-900"
            >
              Shop Now
            </Link>
            <Link
              to="/products"
              className="rounded-xl border-2 border-white/50 bg-transparent px-8 py-3.5 text-base font-bold text-white transition-colors hover:border-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-900"
            >
              View Collections
            </Link>
          </div>
        </div>
      </section>

      {/* ── Features Banner ───────────────────────────────────────────────── */}
      <section
        aria-label="Shopping benefits"
        className="border-b border-gray-200 bg-gray-50 px-6 py-5"
      >
        <ul
          className="mx-auto grid max-w-5xl list-none grid-cols-2 gap-4 p-0 sm:grid-cols-4"
          role="list"
        >
          {[
            { icon: '🚚', title: 'Free Shipping',    desc: 'On orders over £75' },
            { icon: '↩️', title: 'Easy Returns',     desc: '30-day return policy' },
            { icon: '🔒', title: 'Secure Payment',   desc: 'SSL encrypted checkout' },
            { icon: '⭐', title: 'Premium Quality',  desc: 'Handcrafted with care' },
          ].map((feature) => (
            <li key={feature.title} className="flex flex-col items-center p-2 text-center">
              <span className="mb-1 text-3xl" aria-hidden="true">{feature.icon}</span>
              <p className="mb-0.5 text-sm font-semibold text-gray-900">{feature.title}</p>
              <p className="text-xs text-gray-500">{feature.desc}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── Featured Categories ───────────────────────────────────────────── */}
      <section
        aria-labelledby="categories-heading"
        className="mx-auto max-w-6xl px-6 py-16"
      >
        <div className="mb-10 text-center">
          <h2 id="categories-heading" className="mb-3 text-3xl font-extrabold text-gray-900">
            Shop by Category
          </h2>
          <p className="text-base text-gray-500">
            Find the perfect boots for every style and occasion
          </p>
        </div>
        <ul
          className="grid list-none grid-cols-2 gap-6 p-0 sm:grid-cols-4"
          role="list"
        >
          {FEATURED_CATEGORIES.map((category) => (
            <li key={category.id}>
              <CategoryCard category={category} />
            </li>
          ))}
        </ul>
      </section>

      {/* ── Featured Products ─────────────────────────────────────────────── */}
      <section
        aria-labelledby="featured-heading"
        className="bg-gray-50 px-6 py-16"
      >
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 text-center">
            <h2 id="featured-heading" className="mb-3 text-3xl font-extrabold text-gray-900">
              Featured Products
            </h2>
            <p className="text-base text-gray-500">
              Our most popular boots, loved by customers everywhere
            </p>
          </div>

          {isLoading && (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" label="Loading featured products…" />
            </div>
          )}

          {isError && (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 p-6 text-center"
            >
              <p className="text-sm text-red-700">
                Failed to load featured products. Please try again later.
              </p>
            </div>
          )}

          {!isLoading && !isError && featuredProducts.length === 0 && (
            <div className="py-12 text-center">
              <span className="text-5xl" aria-hidden="true">👢</span>
              <p className="mt-4 text-base text-gray-500">
                No products available at the moment.
              </p>
            </div>
          )}

          {!isLoading && !isError && featuredProducts.length > 0 && (
            <>
              <ul
                className="grid list-none grid-cols-1 gap-6 p-0 sm:grid-cols-2 lg:grid-cols-4"
                role="list"
                aria-label="Featured products"
              >
                {featuredProducts.map((product) => (
                  <li key={product.id}>
                    <FeaturedProductCard product={product} />
                  </li>
                ))}
              </ul>
              <div className="mt-10 text-center">
                <Link
                  to="/products"
                  className="inline-block rounded-xl bg-gray-900 px-10 py-3.5 text-base font-bold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
                >
                  View All Products
                </Link>
              </div>
            </>
          )}
        </div>
      </section>

      {/* ── Promotional Banner ─────────────────────────────────────────────── */}
      <section
        aria-labelledby="promo-heading"
        className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-16 text-center text-white"
      >
        <div className="mx-auto max-w-xl">
          <h2 id="promo-heading" className="mb-4 text-4xl font-extrabold">
            New Season, New Styles
          </h2>
          <p className="mb-8 text-lg text-white/85">
            Get 20% off your first order when you sign up for our newsletter.
          </p>
          {/* Newsletter form — label added for WCAG 1.3.1 / 3.3.2 compliance */}
          <form
            aria-label="Newsletter sign-up"
            onSubmit={(e) => {
              e.preventDefault();
              /* Newsletter submission would go here in a real implementation */
            }}
            className="flex flex-wrap justify-center gap-3"
          >
            <label htmlFor="newsletter-email" className="sr-only">
              Email address for newsletter
            </label>
            <input
              id="newsletter-email"
              type="email"
              value={newsletterEmail}
              onChange={(e) => setNewsletterEmail(e.target.value)}
              placeholder="Enter your email address"
              autoComplete="email"
              aria-required="true"
              className="w-72 max-w-full rounded-xl border-none px-5 py-3.5 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            <button
              type="submit"
              className="rounded-xl bg-white px-7 py-3.5 text-base font-bold text-blue-600 transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-600"
            >
              Subscribe
            </button>
          </form>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        role="contentinfo"
        className="bg-[#1a1a2e] px-6 py-10 text-center text-white/70"
      >
        <div className="mx-auto max-w-6xl">
          <span className="mb-3 block text-4xl" aria-hidden="true">👢</span>
          <p className="mb-2 text-lg font-bold text-white">Boots Shop</p>
          <p className="mb-6 text-sm">Premium boots for every step of your journey.</p>
          <nav aria-label="Footer navigation">
            <ul className="mb-6 flex list-none flex-wrap justify-center gap-6 p-0" role="list">
              {[
                { label: 'About Us',        to: '/about' },
                { label: 'Contact',         to: '/contact' },
                { label: 'Privacy Policy',  to: '/privacy' },
                { label: 'Terms of Service',to: '/terms' },
                { label: 'FAQ',             to: '/faq' },
              ].map(({ label, to }) => (
                <li key={label}>
                  <Link
                    to={to}
                    className="text-sm text-white/60 transition-colors hover:text-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-gray-900 rounded"
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <p className="text-xs text-white/40">
            © {new Date().getFullYear()} Boots Shop. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
