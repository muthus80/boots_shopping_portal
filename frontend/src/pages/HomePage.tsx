import React, { useEffect, useState } from 'react';
import { getProducts } from '../api/products';
import { Product, Category } from '../types/index';

const FEATURED_CATEGORIES: Category[] = [
  { id: '1', name: 'Ankle Boots', slug: 'ankle-boots', description: 'Stylish ankle boots for every occasion', parent_id: null, image_url: null, is_active: true, created_at: '', updated_at: '' },
  { id: '2', name: 'Chelsea Boots', slug: 'chelsea-boots', description: 'Classic Chelsea boots', parent_id: null, image_url: null, is_active: true, created_at: '', updated_at: '' },
  { id: '3', name: 'Knee High Boots', slug: 'knee-high-boots', description: 'Elegant knee high boots', parent_id: null, image_url: null, is_active: true, created_at: '', updated_at: '' },
  { id: '4', name: 'Work Boots', slug: 'work-boots', description: 'Durable work boots', parent_id: null, image_url: null, is_active: true, created_at: '', updated_at: '' },
];

const CategoryCard: React.FC<{ category: Category }> = ({ category }) => (
  <div
    style={{
      background: '#f5f5f5',
      borderRadius: '12px',
      padding: '24px',
      textAlign: 'center',
      cursor: 'pointer',
      transition: 'transform 0.2s, box-shadow 0.2s',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)';
      (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
      (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
    }}
  >
    <div style={{ fontSize: '48px', marginBottom: '12px' }}>👢</div>
    <h3 style={{ margin: '0 0 8px', fontSize: '18px', fontWeight: 600, color: '#1a1a1a' }}>
      {category.name}
    </h3>
    {category.description && (
      <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>{category.description}</p>
    )}
  </div>
);

const ProductCard: React.FC<{ product: Product }> = ({ product }) => (
  <div
    style={{
      background: '#fff',
      borderRadius: '12px',
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'pointer',
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)';
      (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
      (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
    }}
  >
    <div
      style={{
        height: '200px',
        background: product.image_url ? `url(${product.image_url}) center/cover no-repeat` : '#e8e8e8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {!product.image_url && <span style={{ fontSize: '64px' }}>👢</span>}
    </div>
    <div style={{ padding: '16px' }}>
      <h4 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600, color: '#1a1a1a' }}>
        {product.name}
      </h4>
      {product.description && (
        <p
          style={{
            margin: '0 0 12px',
            fontSize: '14px',
            color: '#666',
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {product.description}
        </p>
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '18px', fontWeight: 700, color: '#2563eb' }}>
          ${Number(product.base_price).toFixed(2)}
        </span>
        <button
          style={{
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
          onClick={e => {
            e.stopPropagation();
          }}
        >
          View
        </button>
      </div>
    </div>
  </div>
);

export const HomePage: React.FC = () => {
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getProducts({ page: 1, page_size: 8 });
        setFeaturedProducts(result.items);
      } catch (err) {
        setError('Failed to load featured products. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchFeatured();
  }, []);

  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', color: '#1a1a1a' }}>
      {/* Hero Section */}
      <section
        style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          color: '#fff',
          padding: '80px 24px',
          textAlign: 'center',
        }}
      >
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <div style={{ fontSize: '72px', marginBottom: '16px' }}>👢</div>
          <h1
            style={{
              fontSize: '48px',
              fontWeight: 800,
              margin: '0 0 16px',
              lineHeight: 1.2,
            }}
          >
            Step Into Style
          </h1>
          <p
            style={{
              fontSize: '20px',
              color: 'rgba(255,255,255,0.8)',
              margin: '0 0 32px',
              lineHeight: 1.6,
            }}
          >
            Discover our premium collection of boots crafted for every adventure, every season, every you.
          </p>
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              style={{
                background: '#2563eb',
                color: '#fff',
                border: 'none',
                borderRadius: '10px',
                padding: '14px 32px',
                fontSize: '16px',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'background 0.2s',
              }}
            >
              Shop Now
            </button>
            <button
              style={{
                background: 'transparent',
                color: '#fff',
                border: '2px solid rgba(255,255,255,0.5)',
                borderRadius: '10px',
                padding: '14px 32px',
                fontSize: '16px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              View Collections
            </button>
          </div>
        </div>
      </section>

      {/* Features Banner */}
      <section
        style={{
          background: '#f8fafc',
          borderBottom: '1px solid #e2e8f0',
          padding: '20px 24px',
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            textAlign: 'center',
          }}
        >
          {[
            { icon: '🚚', title: 'Free Shipping', desc: 'On orders over $75' },
            { icon: '↩️', title: 'Easy Returns', desc: '30-day return policy' },
            { icon: '🔒', title: 'Secure Payment', desc: 'SSL encrypted checkout' },
            { icon: '⭐', title: 'Premium Quality', desc: 'Handcrafted with care' },
          ].map(feature => (
            <div key={feature.title} style={{ padding: '8px' }}>
              <span style={{ fontSize: '28px' }}>{feature.icon}</span>
              <p style={{ margin: '4px 0 2px', fontWeight: 600, fontSize: '14px' }}>{feature.title}</p>
              <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Featured Categories */}
      <section style={{ padding: '64px 24px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h2 style={{ fontSize: '32px', fontWeight: 800, margin: '0 0 12px' }}>Shop by Category</h2>
          <p style={{ fontSize: '16px', color: '#64748b', margin: 0 }}>
            Find the perfect boots for every style and occasion
          </p>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '24px',
          }}
        >
          {FEATURED_CATEGORIES.map(category => (
            <CategoryCard key={category.id} category={category} />
          ))}
        </div>
      </section>

      {/* Featured Products */}
      <section style={{ padding: '64px 24px', background: '#f8fafc' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <h2 style={{ fontSize: '32px', fontWeight: 800, margin: '0 0 12px' }}>Featured Products</h2>
            <p style={{ fontSize: '16px', color: '#64748b', margin: 0 }}>
              Our most popular boots, loved by customers everywhere
            </p>
          </div>

          {loading && (
            <div style={{ textAlign: 'center', padding: '48px' }}>
              <div
                style={{
                  display: 'inline-block',
                  width: '48px',
                  height: '48px',
                  border: '4px solid #e2e8f0',
                  borderTopColor: '#2563eb',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              <p style={{ marginTop: '16px', color: '#64748b' }}>Loading featured products...</p>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {error && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '10px',
                padding: '20px',
                textAlign: 'center',
                color: '#dc2626',
              }}
            >
              <p style={{ margin: 0 }}>{error}</p>
            </div>
          )}

          {!loading && !error && featuredProducts.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px', color: '#64748b' }}>
              <span style={{ fontSize: '48px' }}>👢</span>
              <p style={{ marginTop: '16px', fontSize: '16px' }}>No products available at the moment.</p>
            </div>
          )}

          {!loading && !error && featuredProducts.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                gap: '24px',
              }}
            >
              {featuredProducts.map(product => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}

          {!loading && !error && featuredProducts.length > 0 && (
            <div style={{ textAlign: 'center', marginTop: '40px' }}>
              <button
                style={{
                  background: '#1a1a2e',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '14px 40px',
                  fontSize: '16px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                View All Products
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Promotional Banner */}
      <section
        style={{
          background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
          color: '#fff',
          padding: '64px 24px',
          textAlign: 'center',
        }}
      >
        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
          <h2 style={{ fontSize: '36px', fontWeight: 800, margin: '0 0 16px' }}>
            New Season, New Styles
          </h2>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.85)', margin: '0 0 32px' }}>
            Get 20% off your first order when you sign up for our newsletter.
          </p>
          <div
            style={{
              display: 'flex',
              gap: '12px',
              justifyContent: 'center',
              flexWrap: 'wrap',
            }}
          >
            <input
              type="email"
              placeholder="Enter your email address"
              style={{
                padding: '14px 20px',
                borderRadius: '10px',
                border: 'none',
                fontSize: '16px',
                width: '300px',
                maxWidth: '100%',
                outline: 'none',
              }}
            />
            <button
              style={{
                background: '#fff',
                color: '#2563eb',
                border: 'none',
                borderRadius: '10px',
                padding: '14px 28px',
                fontSize: '16px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Subscribe
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          background: '#1a1a2e',
          color: 'rgba(255,255,255,0.7)',
          padding: '40px 24px',
          textAlign: 'center',
        }}
      >
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>👢</div>
          <p style={{ margin: '0 0 8px', fontSize: '18px', fontWeight: 700, color: '#fff' }}>
            Boots Shop
          </p>
          <p style={{ margin: '0 0 24px', fontSize: '14px' }}>
            Premium boots for every step of your journey.
          </p>
          <div
            style={{
              display: 'flex',
              gap: '24px',
              justifyContent: 'center',
              flexWrap: 'wrap',
              marginBottom: '24px',
            }}
          >
            {['About Us', 'Contact', 'Privacy Policy', 'Terms of Service', 'FAQ'].map(link => (
              <a
                key={link}
                href="#"
                style={{ color: 'rgba(255,255,255,0.6)', textDecoration: 'none', fontSize: '14px' }}
              >
                {link}
              </a>
            ))}
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
            © {new Date().getFullYear()} Boots Shop. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;