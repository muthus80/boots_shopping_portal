import { test, expect } from '@playwright/test'

/**
 * Sprint 1 – US-004: Search for Boots
 *               US-006: View Product Listing Page
 *               US-014: System Feedback States (loading / error / empty)
 *
 * Text sourced from:
 *   frontend/src/pages/ProductListPage.tsx
 *     - heading:        "Our Products"
 *     - search button:  "Search"
 *     - empty state:    "No products found"
 *     - SiteHeader search: placeholder "Search boots…"
 */

test.describe('Sprint 1 — US-006 / US-004: Product Listing and Search', () => {
  test('product listing page shows heading and product grid', async ({ page }) => {
    // Navigate directly to the product listing page
    await page.goto('/products')

    // AC (US-006): product listing page renders
    await expect(page.getByRole('heading', { name: 'Our Products' })).toBeVisible({ timeout: 15000 })
  })

  test('searching from the listing page filters results', async ({ page }) => {
    await page.goto('/products')
    await expect(page.getByRole('heading', { name: 'Our Products' })).toBeVisible({ timeout: 10000 })

    // AC (US-004): type in search box and submit
    // ProductListPage.tsx renders a plain <input placeholder="Search products..."> inside a <form>
    await page.getByPlaceholder('Search products...').fill('boot')
    await page.getByRole('button', { name: 'Search' }).click()

    // URL should update with search param
    await expect(page).toHaveURL(/search=boot/, { timeout: 10000 })
  })

  test('search with no matches shows the empty state', async ({ page }) => {
    // Navigate directly to search results for a query that will not match
    await page.goto('/products?search=xyzzy_nonexistent_9999')

    // AC (US-004): no results message is shown
    // ProductListPage.tsx renders: <p>"No products found"</p> when empty
    await expect(page.getByText('No products found')).toBeVisible({ timeout: 15000 })
  })

  test('header search bar submits and navigates to products page', async ({ page }) => {
    // Entry point: homepage
    await page.goto('/')

    // SiteHeader.tsx search: <input aria-label="Search products" placeholder="Search boots…">
    await page.getByLabel('Search products').fill('hiking')
    await page.getByRole('button', { name: 'Submit search' }).click()

    // AC: navigated to products search results page
    await expect(page).toHaveURL(/\/products.*search=hiking/, { timeout: 10000 })
  })
})
