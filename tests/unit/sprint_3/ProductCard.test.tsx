import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ProductCard } from './ProductCard';
import type { Product } from '../../types/index';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const baseProduct: Product = {
  id: 'prod-1',
  name: 'Trek Leather Boot',
  slug: 'trek-leather-boot',
  description: 'A durable hiking boot',
  category_id: 'cat-1',
  brand: 'OutdoorPro',
  base_price: 120,
  sale_price: null,
  image_url: null,
  images: [],
  is_active: true,
  is_featured: false,
  average_rating: null,
  review_count: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const renderCard = (product: Product) =>
  render(
    <BrowserRouter>
      <ProductCard product={product} />
    </BrowserRouter>
  );

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ProductCard', () => {
  it('renders the product name', () => {
    renderCard(baseProduct);
    expect(screen.getByText('Trek Leather Boot')).toBeInTheDocument();
  });

  it('renders the brand', () => {
    renderCard(baseProduct);
    expect(screen.getByText('OutdoorPro')).toBeInTheDocument();
  });

  it('renders the base price when no sale price', () => {
    renderCard(baseProduct);
    expect(screen.getByText(/£120\.00/)).toBeInTheDocument();
  });

  it('renders the sale price when present', () => {
    const saleProduct: Product = { ...baseProduct, sale_price: 90 };
    renderCard(saleProduct);
    expect(screen.getByText(/£90\.00/)).toBeInTheDocument();
  });

  it('shows the SALE badge when sale_price is lower than base_price', () => {
    const saleProduct: Product = { ...baseProduct, sale_price: 90 };
    renderCard(saleProduct);
    expect(screen.getByText('SALE')).toBeInTheDocument();
  });

  it('does not show SALE badge when there is no discount', () => {
    renderCard(baseProduct);
    expect(screen.queryByText('SALE')).not.toBeInTheDocument();
  });

  it('shows strikethrough base price when on sale', () => {
    const saleProduct: Product = { ...baseProduct, sale_price: 90 };
    renderCard(saleProduct);
    expect(screen.getByText(/£120\.00/)).toBeInTheDocument();
  });

  it('links to the correct product detail URL', () => {
    renderCard(baseProduct);
    const link = screen.getByRole('link', { name: /View Trek Leather Boot/i });
    expect(link).toHaveAttribute('href', '/products/prod-1');
  });

  it('renders a product image when images array has entries', () => {
    const productWithImage: Product = {
      ...baseProduct,
      images: ['https://example.com/boot.jpg'],
    };
    renderCard(productWithImage);
    const img = screen.getByRole('img', { name: 'Trek Leather Boot' });
    expect(img).toHaveAttribute('src', 'https://example.com/boot.jpg');
  });

  it('falls back to image_url when images array is empty', () => {
    const productWithImageUrl: Product = {
      ...baseProduct,
      images: [],
      image_url: 'https://example.com/fallback.jpg',
    };
    renderCard(productWithImageUrl);
    const img = screen.getByRole('img', { name: 'Trek Leather Boot' });
    expect(img).toHaveAttribute('src', 'https://example.com/fallback.jpg');
  });

  it('does not render the brand section when brand is null', () => {
    const noBrand: Product = { ...baseProduct, brand: null };
    renderCard(noBrand);
    expect(screen.queryByText('OutdoorPro')).not.toBeInTheDocument();
  });
});
