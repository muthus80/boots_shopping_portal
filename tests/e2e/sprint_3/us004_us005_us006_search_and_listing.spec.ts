import { test, expect } from '@playwright/test'

test.describe('Sprint 3 — US-004: Search for Boots', () => {
  test('user searches for a keyword and sees results page', async ({ page }) => {
    // Entry: user is on the homepage
    await page.goto('/')

    // AC: header is present with search bar — SiteHeader renders aria-label "Search products"
    await expect(page.getByRole('banner')).toBeVisible()

    // Use the search bar in the header — placeholder from SiteHeader.tsx ("Search boots…")
    // Use first() to pick the header instance (SearchResultsPage also has a search input)
    await page.getByPlaceholder('Search boots…').first().fill('hiking')
    await page.getByLabel('Submit search').first().click()

    // AC: taken to search results page
    await expect(page).toHaveURL(/search.*q=hiking/, { timeout: 10000 })

    // AC: results page loaded — from SearchResultsPage.tsx heading pattern
    await expect(page.getByRole('heading', { name: /search results for/i })).toBeVisible()
  })

  test('search with no results shows no-results message', async ({ page }) => {
    // Navigate directly to search results for a query that won't match anything
    await page.goto('/search?q=xyznonexistentbootquery99999')

    // AC: no results message — from SearchResultsPage.tsx lines 148-153
    await expect(
      page.getByText('No results found for your search')
    ).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Sprint 3 — US-006: View Product Listing Page', () => {
  test('clicking a category from homepage navigates to product listing', async ({ page }) => {
    // Entry: homepage
    await page.goto('/')

    // AC: click on a category card — from HomePage.tsx FEATURED_CATEGORIES
    // "Work Boots" is in the featured categories list
    await page.getByRole('link', { name: 'Work Boots' }).first().click()

    // AC: taken to product listing page
    await expect(page).toHaveURL(/products.*work-boots/, { timeout: 10000 })
  })

  test('clicking the site logo returns to homepage', async ({ page }) => {
    // Navigate to a product page first
    await page.goto('/products')

    // AC (US-012): clicking site logo returns to homepage — from SiteHeader.tsx aria-label
    await page.getByRole('link', { name: 'Boots Shop — go to homepage' }).click()
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })
})

test.describe('Sprint 3 — US-012: Consistent Site Navigation', () => {
  test('header is present on every page with links to categories, search, account, and cart', async ({ page }) => {
    // Entry: homepage
    await page.goto('/')

    // AC: header is present — SiteHeader has role="banner"
    const header = page.getByRole('banner')
    await expect(header).toBeVisible()

    // AC: search bar is present — from SiteHeader.tsx placeholder "Search boots…"
    // Use the banner-scoped search placeholder to avoid ambiguity with page search inputs
    await expect(page.getByRole('banner').getByPlaceholder('Search boots…')).toBeVisible()

    // AC: cart link present — from SiteHeader aria-label
    await expect(page.getByRole('link', { name: /shopping cart/i })).toBeVisible()

    // AC: account links — Sign In or My Orders depending on auth state
    // Since we're not logged in, "Sign in to your account" is visible
    await expect(page.getByRole('link', { name: 'Sign in to your account' })).toBeVisible()

    // Verify header is also present on product listing page
    await page.goto('/products')
    await expect(page.getByRole('banner')).toBeVisible()
    await expect(page.getByRole('banner').getByPlaceholder('Search boots…')).toBeVisible()
  })
})
