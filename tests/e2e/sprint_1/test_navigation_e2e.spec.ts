import { test, expect } from '@playwright/test'

test.describe('Sprint 1 — US-012: Consistent Site Navigation', () => {
  test('header is present on every page with navigation links and logo', async ({ page }) => {
    await page.goto('/')

    // AC: header is present with role="banner" (SiteHeader.tsx: <header role="banner">)
    await expect(page.getByRole('banner')).toBeVisible()

    // AC: site logo link — SiteHeader.tsx: aria-label="Boots Shop — go to homepage"
    await expect(page.getByRole('link', { name: /boots shop.*homepage/i })).toBeVisible()

    // AC: search bar — SiteHeader.tsx has two SearchBar instances (desktop + mobile menu).
    // Use the desktop one inside the visible "hidden sm:block" wrapper.
    // getByLabel returns 2 matches on desktop; narrow to first visible one.
    await expect(page.getByLabel('Search products').first()).toBeVisible()

    // AC: cart link — SiteHeader.tsx: aria-label="Shopping cart"
    await expect(page.getByRole('link', { name: /shopping cart/i })).toBeVisible()
  })

  test('clicking the site logo returns user to the homepage', async ({ page }) => {
    // Navigate away from home first
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // AC: click logo → returns to homepage
    await page.getByRole('link', { name: /boots shop.*homepage/i }).click()
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('header navigation is present on the products listing page', async ({ page }) => {
    await page.goto('/products')
    await expect(page.getByRole('banner')).toBeVisible()
    await expect(page.getByRole('link', { name: /boots shop.*homepage/i })).toBeVisible()
  })

  test('header navigation is present on the login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('banner')).toBeVisible()
    // SiteHeader AccountActions renders Register link when user is not logged in
    // SiteHeader.tsx: <Link to="/register" ...>Register</Link>
    await expect(page.getByRole('link', { name: 'Register' })).toBeVisible()
    // Logo link always visible
    await expect(page.getByRole('link', { name: /boots shop.*homepage/i })).toBeVisible()
  })
})

test.describe('Sprint 1 — US-003: Order History Navigation', () => {
  test('logged-out user accessing orders is redirected to login page', async ({ page }) => {
    // App.tsx wraps /orders in <ProtectedRoute> which redirects to /login
    await page.goto('/orders')
    await expect(page).toHaveURL(/login/, { timeout: 10000 })
  })
})

test.describe('Sprint 1 — US-014: System Feedback States', () => {
  test('order history page shows empty state message when no orders exist', async ({ page }) => {
    // Register and log in
    const email = `emptyorders_${Date.now()}@example.com`
    const password = 'StrongPass1!'

    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel(/confirm password/i).fill(password)
    await page.getByRole('button', { name: 'Create Account' }).click()
    // RegisterPage.tsx navigates to / after registration
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Log in
    await page.goto('/login')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign In' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Navigate to orders
    await page.goto('/orders')

    // AC: US-014 — "No orders yet" message shown in OrdersPage.tsx
    await expect(page.getByRole('heading', { name: 'No orders yet' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/it will appear here/i)).toBeVisible()
  })
})
