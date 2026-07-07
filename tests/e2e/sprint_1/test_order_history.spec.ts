import { test, expect } from '@playwright/test'

/**
 * Sprint 1 – US-003: View Order History
 *
 * Text sourced from frontend/src/pages/OrdersPage.tsx:
 *   - heading: "Order History"
 *   - empty state h3: "No orders yet"
 *   - empty state p: "When you place an order, it will appear here."
 */

test.describe('Sprint 1 — US-003: View Order History', () => {
  test('logged-in user with no orders sees the empty state', async ({ page }) => {
    // Register a fresh user so they have no orders
    await page.goto('/register')
    const email = `orders_empty_${Date.now()}@example.com`
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('TestPass1!')
    await page.getByLabel('Confirm password').fill('TestPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Navigate to orders page
    await page.goto('/orders')

    // AC: Order History page heading visible
    await expect(page.getByRole('heading', { name: 'Order History' })).toBeVisible()

    // AC: empty-orders message shown (OrdersPage.tsx renders "No orders yet")
    await expect(page.getByRole('heading', { name: 'No orders yet' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('When you place an order, it will appear here.')).toBeVisible()
  })

  test('unauthenticated user is redirected to login when accessing orders', async ({ page }) => {
    // AC (US-013 / session gate): attempting to access /orders without auth redirects to login
    await page.goto('/orders')
    // ProtectedRoute in App.tsx redirects to /login
    await expect(page).toHaveURL(/login/, { timeout: 10000 })
  })
})
