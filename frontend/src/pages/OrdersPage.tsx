import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { useAuth } from '../stores/authStore';
import { Order, OrderItem } from '../types/index';

const statusColors: Record<string, string> = {
  pending: '#f59e0b',
  confirmed: '#3b82f6',
  processing: '#8b5cf6',
  shipped: '#06b6d4',
  delivered: '#10b981',
  cancelled: '#ef4444',
  refunded: '#6b7280',
};

const formatCurrency = (amount: number): string =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount);

const formatDate = (dateStr: string): string =>
  new Intl.DateTimeFormat('en-GB', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(dateStr));

interface OrderCardProps {
  order: Order;
}

const OrderCard: React.FC<OrderCardProps> = ({ order }) => {
  const [expanded, setExpanded] = useState(false);

  const statusColor = statusColors[order.status] ?? '#6b7280';

  return (
    <div
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        marginBottom: '16px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.07)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          backgroundColor: '#f9fafb',
          cursor: 'pointer',
          userSelect: 'none',
        }}
        onClick={() => setExpanded((prev) => !prev)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') setExpanded((prev) => !prev);
        }}
        aria-expanded={expanded}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ fontWeight: 600, fontSize: '15px', color: '#111827' }}>
            Order #{order.id.slice(0, 8).toUpperCase()}
          </span>
          <span style={{ fontSize: '13px', color: '#6b7280' }}>
            Placed on {formatDate(order.created_at)}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span
            style={{
              display: 'inline-block',
              padding: '3px 10px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 600,
              color: '#fff',
              backgroundColor: statusColor,
              textTransform: 'capitalize',
            }}
          >
            {order.status}
          </span>
          <span style={{ fontWeight: 700, fontSize: '15px', color: '#111827' }}>
            {formatCurrency(order.total_amount)}
          </span>
          <span style={{ fontSize: '18px', color: '#9ca3af' }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ padding: '16px 20px' }}>
          {order.shipping_address && (
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ margin: '0 0 6px', fontSize: '13px', color: '#6b7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Shipping Address
              </h4>
              <p style={{ margin: 0, fontSize: '14px', color: '#374151', lineHeight: '1.5' }}>
                {order.shipping_address.address_line1}
                {order.shipping_address.address_line2 ? `, ${order.shipping_address.address_line2}` : ''},
                {' '}{order.shipping_address.city}, {order.shipping_address.state} {order.shipping_address.postal_code},
                {' '}{order.shipping_address.country}
              </p>
            </div>
          )}

          <h4 style={{ margin: '0 0 10px', fontSize: '13px', color: '#6b7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Items
          </h4>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 600 }}>Product</th>
                <th style={{ textAlign: 'center', padding: '6px 8px', color: '#6b7280', fontWeight: 600 }}>Qty</th>
                <th style={{ textAlign: 'right', padding: '6px 8px', color: '#6b7280', fontWeight: 600 }}>Unit Price</th>
                <th style={{ textAlign: 'right', padding: '6px 8px', color: '#6b7280', fontWeight: 600 }}>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((item: OrderItem) => (
                <tr key={item.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '8px 8px', color: '#111827' }}>
                    <div style={{ fontWeight: 500 }}>{item.product_name}</div>
                    {(item.size || item.color) && (
                      <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                        {item.size && `Size: ${item.size}`}
                        {item.size && item.color && ' / '}
                        {item.color && `Color: ${item.color}`}
                      </div>
                    )}
                  </td>
                  <td style={{ textAlign: 'center', padding: '8px 8px', color: '#374151' }}>{item.quantity}</td>
                  <td style={{ textAlign: 'right', padding: '8px 8px', color: '#374151' }}>
                    {formatCurrency(item.unit_price)}
                  </td>
                  <td style={{ textAlign: 'right', padding: '8px 8px', color: '#111827', fontWeight: 600 }}>
                    {formatCurrency(item.unit_price * item.quantity)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3} style={{ textAlign: 'right', padding: '10px 8px', fontWeight: 700, color: '#111827' }}>
                  Total
                </td>
                <td style={{ textAlign: 'right', padding: '10px 8px', fontWeight: 700, color: '#111827' }}>
                  {formatCurrency(order.total_amount)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
};

export const OrdersPage: React.FC = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const fetchOrders = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<Order[]>('/api/v1/checkout/orders');
        setOrders(response.data);
      } catch (err: unknown) {
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { data?: { detail?: string } } };
          setError(axiosErr.response?.data?.detail ?? 'Failed to load orders.');
        } else {
          setError('Failed to load orders.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [user]);

  if (!user) {
    return (
      <div style={{ maxWidth: '720px', margin: '60px auto', padding: '0 16px', textAlign: 'center' }}>
        <h2 style={{ color: '#111827' }}>Please log in to view your orders.</h2>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '800px', margin: '40px auto', padding: '0 16px' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 700, color: '#111827', marginBottom: '8px' }}>
        Order History
      </h1>
      <p style={{ color: '#6b7280', marginBottom: '28px', fontSize: '15px' }}>
        View and track all your past orders.
      </p>

      {loading && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: '#6b7280', fontSize: '16px' }}>
          Loading your orders…
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            padding: '16px 20px',
            color: '#b91c1c',
            fontSize: '14px',
          }}
        >
          {error}
        </div>
      )}

      {!loading && !error && orders.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '64px 0',
            color: '#9ca3af',
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📦</div>
          <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#374151', marginBottom: '8px' }}>
            No orders yet
          </h3>
          <p style={{ fontSize: '14px' }}>
            When you place an order, it will appear here.
          </p>
        </div>
      )}

      {!loading && !error && orders.length > 0 && (
        <div>
          {orders.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      )}
    </div>
  );
};

export default OrdersPage;