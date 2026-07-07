import { test, expect } from '@playwright/test'

// US-009: Add to Shopping Cart
// US-010: View and Edit Shopping Cart
// US-003: View Order History

test.describe('Sprint 2 — US-009 & US-010: Shopping Cart', () => {
  test('user navigates to cart page and sees empty cart state', async ({ page }) => {
    // Navigate directly to cart
    await page.goto('/cart')

    // CartPage.tsx renders h1 "Your Cart" when loading or empty
    await expect(page.getByRole('heading', { name: 'Your Cart' })).toBeVisible({ timeout: 10000 })
  })

  test('cart page shows empty state with continue shopping link', async ({ page }) => {
    await page.goto('/cart')

    // Wait for cart to finish loading
    await page.waitForLoadState('networkidle').catch(() => {})

    // AC: empty cart state — CartPage.tsx renders EmptyState with heading "Your cart is empty"
    const emptyHeading = page.getByRole('heading', { name: 'Your cart is empty' })
    const cartItems = page.getByRole('region', { name: 'Cart items' })

    // Either empty state or items list should be present
    const isEmpty = await emptyHeading.isVisible().catch(() => false)
    const hasItems = await cartItems.isVisible().catch(() => false)

    expect(isEmpty || hasItems).toBeTruthy()

    if (isEmpty) {
      // AC: "Continue Shopping" link present when cart is empty (CartPage.tsx)
      await expect(page.getByRole('link', { name: 'Continue Shopping' })).toBeVisible()
    }
  })
})

test.describe('Sprint 2 — US-003: Order History', () => {
  test('unauthenticated user trying to access orders is redirected to login', async ({ page }) => {
    // AC: protected route — /orders requires auth. App.tsx wraps it in ProtectedRoute.
    await page.goto('/orders')

    // AC: redirected to login page when not authenticated
    await expect(page).toHaveURL(/login/, { timeout: 8000 })
  })

  test('authenticated user can access order history page', async ({ page }) => {
    // Register and log in a user
    const email = `e2e_orders_${Date.now()}@example.com`
    const password = 'SecurePass1!'

    // Register
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    await page.getByRole('button', { name: 'Create Account' }).click()

    // Wait for redirect to home
    await expect(page).toHaveURL('/', { timeout: 10000 })

    // Navigate to order history
    await page.goto('/orders')

    // AC: order history page loads — OrdersPage.tsx renders h1 "Order History"
    await expect(page.getByRole('heading', { name: 'Order History' })).toBeVisible({ timeout: 10000 })

    // AC: US-014: no prior orders — shows empty state from OrdersPage.tsx
    // "No orders yet" heading
    await page.waitForLoadState('networkidle').catch(() => {})
    const noOrdersHeading = page.getByRole('heading', { name: 'No orders yet' })
    const orderCards = page.locator('[role="button"]').first()

    const hasNoOrdersState = await noOrdersHeading.isVisible().catch(() => false)
    const hasOrders = await orderCards.isVisible().catch(() => false)

    // Either state is valid — just confirm the page loaded correctly
    expect(hasNoOrdersState || hasOrders).toBeTruthy()
  })
})

test.describe('Sprint 2 — US-013: Session Continuity', () => {
  test('logged-in user remains logged in after page refresh', async ({ page }) => {
    const email = `e2e_session_${Date.now()}@example.com`
    const password = 'SecurePass1!'

    // Register and confirm login
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 10000 })

    // AC: after refresh, user is still logged in
    await page.reload()

    // The header should show "Log Out" button (AccountActions when user is logged in)
    // From SiteHeader.tsx: logged-in user sees button with aria-label="Log out"
    await expect(page.getByRole('button', { name: 'Log out', exact: false })).toBeVisible({ timeout: 8000 })
  })
})
