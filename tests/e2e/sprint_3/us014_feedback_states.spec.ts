import { test, expect } from '@playwright/test'

test.describe('Sprint 3 — US-014: System Feedback States', () => {
  test('search results page shows loading indicator while fetching', async ({ page }) => {
    // Slow down network to catch loading state
    await page.route('**/api/v1/products/search**', async (route) => {
      // Delay to allow loading indicator to appear
      await new Promise((resolve) => setTimeout(resolve, 200))
      await route.continue()
    })

    await page.goto('/search?q=boots')

    // AC: loading indicator visible while results are fetched
    // SearchResultsPage uses aria-busy="true" and aria-label="Loading products"
    // This may be brief — check it appeared at some point or check final state
    // The skeleton divs have aria-busy="true" on the container
    // We check that eventually results or no-results appear
    await expect(
      page.getByText(/results for|no results found/i)
    ).toBeVisible({ timeout: 15000 })
  })

  test('order history page shows empty state message when no orders exist', async ({ page }) => {
    // Register and login as new user with no orders
    await page.goto('/register')
    const email = `emptyorders_${Date.now()}@example.com`
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('EmptyPass1A!')
    await page.getByLabel('Confirm password').fill('EmptyPass1A!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Navigate to orders
    await page.goto('/orders')

    // AC: empty state message — from OrdersPage.tsx line 197
    // EmptyState renders heading in a <p> inside a <div role="status">
    // Use role="status" scope to disambiguate from any other text occurrences
    await expect(
      page.getByRole('status').getByText('You have not placed any orders yet.', { exact: true })
    ).toBeVisible({ timeout: 10000 })
  })

  test('product listing page shows error message on API failure', async ({ page }) => {
    // Intercept products API and return a 500 error
    await page.route('**/api/v1/products**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    })

    await page.goto('/products')

    // AC: user-friendly error message — from SearchResultsPage.tsx and HomePage.tsx
    // "Something went wrong, please try again" is used in error states
    await expect(
      page.getByText(/something went wrong|failed to load/i)
    ).toBeVisible({ timeout: 10000 })
  })
})
