import { test, expect } from '@playwright/test'

/**
 * Sprint 1 – US-012: Consistent Site Navigation
 *               US-013: Session Continuity
 *
 * Text sourced from:
 *   frontend/src/components/layout/SiteHeader.tsx
 *     - logo aria-label: "Boots Shop — go to homepage"
 *     - cart aria-label: "Shopping cart"
 *     - sign-in aria-label: "Sign in to your account"
 *     - register link text: "Register"
 */

test.describe('Sprint 1 — US-012: Consistent Site Navigation', () => {
  test('header is present on every page with links to categories, search, account, and cart', async ({ page }) => {
    // AC: header visible on homepage
    await page.goto('/')
    const header = page.getByRole('banner')
    await expect(header).toBeVisible()

    // AC: cart link present (aria-label from SiteHeader.tsx: "Shopping cart")
    await expect(header.getByRole('link', { name: 'Shopping cart' })).toBeVisible()

    // AC: account / sign-in link present
    await expect(header.getByRole('link', { name: 'Sign in to your account' })).toBeVisible()

    // AC: register link present
    await expect(header.getByRole('link', { name: 'Register' })).toBeVisible()

    // AC: search bar present (aria-label "Search products" on the input)
    await expect(header.getByLabel('Search products')).toBeVisible()

    // AC: header also visible on products page
    await page.goto('/products')
    await expect(page.getByRole('banner')).toBeVisible()

    // AC: header present on login page
    await page.goto('/login')
    await expect(page.getByRole('banner')).toBeVisible()
  })

  test('clicking the site logo returns user to the homepage', async ({ page }) => {
    // Navigate away first
    await page.goto('/login')

    // AC: logo link has aria-label "Boots Shop — go to homepage" (SiteHeader.tsx)
    await page.getByRole('link', { name: 'Boots Shop — go to homepage' }).click()

    // AC: lands on homepage
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })
})

test.describe('Sprint 1 — US-013: Session Continuity', () => {
  test('logged-in user stays logged in after page refresh', async ({ page }) => {
    // Register and log in
    await page.goto('/register')
    const email = `session_test_${Date.now()}@example.com`
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('TestPass1!')
    await page.getByLabel('Confirm password').fill('TestPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // AC (US-013): refresh the page — user stays logged in
    await page.reload()

    // If logged in, the header should show "My Orders" link and "Log Out" button
    // (SiteHeader.tsx AccountActions: shows "My Orders" aria-label and "Log Out" button when user is set)
    await expect(page.getByRole('link', { name: 'View my orders' })).toBeVisible({ timeout: 10000 })
  })

  test('unauthenticated user accessing protected route is redirected to login', async ({ page }) => {
    // AC (US-013): session token expired / not present → redirect to login
    await page.goto('/orders')
    await expect(page).toHaveURL(/login/, { timeout: 10000 })

    await page.goto('/checkout')
    await expect(page).toHaveURL(/login/, { timeout: 10000 })
  })
})
