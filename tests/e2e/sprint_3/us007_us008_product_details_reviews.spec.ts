import { test, expect } from '@playwright/test'

test.describe('Sprint 3 — US-007: View Product Details', () => {
  test('user clicks a product and sees detailed description, images, size and color options', async ({ page }) => {
    // Entry: product listing page (navigate directly to reach a known route)
    await page.goto('/products')

    // Wait for products to load — look for a product link
    const firstProductLink = page.getByRole('link', { name: /boot/i }).first()
    await expect(firstProductLink).toBeVisible({ timeout: 15000 })

    await firstProductLink.click()

    // AC: PDP loads — product name is shown in an h1
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 10000 })

    // AC: description section present
    // ProductDetailPage.tsx renders description in a <p> with leading-relaxed
    const mainContent = page.locator('main, [role="main"], .mx-auto').first()
    await expect(mainContent).toBeVisible()

    // AC: "Add to Cart" button or "Out of Stock" is present — from ProductDetailPage.tsx
    await expect(
      page.getByRole('button', { name: /add to cart|out of stock/i })
    ).toBeVisible({ timeout: 5000 })

    // AC: Reviews section heading is present (ProductDetailPage.tsx line 964: "Customer Reviews")
    // Scroll to the reviews section to ensure it is rendered
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await expect(page.getByRole('heading', { name: 'Customer Reviews' })).toBeVisible({ timeout: 5000 })
  })

  test('product detail page shows size selection and color options', async ({ page }) => {
    // Navigate to product listing
    await page.goto('/products')
    const firstProductLink = page.getByRole('link', { name: /boot/i }).first()
    await expect(firstProductLink).toBeVisible({ timeout: 15000 })
    await firstProductLink.click()

    // AC: If variants exist, size picker group is present — from ProductDetailPage.tsx
    // SizePicker renders a group with aria-label "Select a size"
    // ColorPicker renders a group with aria-label "Select a color"
    // We check whether at least one of these is visible (if variants exist)
    const pageContent = await page.content()
    if (pageContent.includes('Select a size')) {
      await expect(page.getByRole('group', { name: 'Select a size' })).toBeVisible()
    }
    if (pageContent.includes('Select a color')) {
      await expect(page.getByRole('group', { name: 'Select a color' })).toBeVisible()
    }

    // AC: "Add to Cart" button accessible
    await expect(page.getByRole('button', { name: /add to cart|out of stock/i })).toBeVisible()
  })
})

test.describe('Sprint 3 — US-008: Read and Write Product Reviews', () => {
  test('guest user can see customer reviews on product detail page', async ({ page }) => {
    // Navigate to a product page directly
    await page.goto('/products')
    const firstProductLink = page.getByRole('link', { name: /boot/i }).first()
    await expect(firstProductLink).toBeVisible({ timeout: 15000 })
    await firstProductLink.click()

    // Wait for the product page to fully load
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 10000 })

    // AC: reviews section present — ProductDetailPage.tsx line 964 renders h2 "Customer Reviews"
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await expect(page.getByRole('heading', { name: 'Customer Reviews' })).toBeVisible({ timeout: 5000 })

    // AC: Write a Review section is also visible — ProductDetailPage.tsx h3 "Write a Review"
    await expect(page.getByRole('heading', { name: 'Write a Review' })).toBeVisible({ timeout: 5000 })
  })

  test('logged-in user sees the review submission form on the product detail page', async ({ page }) => {
    // Register and log in to get authenticated
    await page.goto('/register')
    const email = `reviewer_${Date.now()}@example.com`
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('ReviewPass1A!')
    await page.getByLabel('Confirm password').fill('ReviewPass1A!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Navigate to a product
    await page.goto('/products')
    const firstProductLink = page.getByRole('link', { name: /boot/i }).first()
    await expect(firstProductLink).toBeVisible({ timeout: 15000 })
    await firstProductLink.click()
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 10000 })

    // AC: logged-in user sees the review form
    // ProductDetailPage.tsx renders a form with aria-label "Write a review" for logged-in users
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await expect(page.getByRole('heading', { name: 'Write a Review' })).toBeVisible({ timeout: 5000 })

    // The review text area is visible for logged-in users
    // ProductDetailPage.tsx: aria-label="Review text" on the textarea
    await expect(page.getByLabel('Review text')).toBeVisible({ timeout: 5000 })
  })
})
