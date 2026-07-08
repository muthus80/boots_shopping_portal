import { test, expect } from '@playwright/test'

test.describe('Sprint 3 — US-001/US-002: Registration and Login', () => {
  test('user registers with valid credentials and sees confirmation', async ({ page }) => {
    // Entry: user visits the registration page
    await page.goto('/register')

    // AC: registration page is displayed
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()

    const uniqueEmail = `testuser_${Date.now()}@example.com`

    // Fill out registration form using exact aria-labels from RegisterPage.tsx
    // Use { exact: true } to disambiguate 'Password' from 'Confirm password'
    await page.getByLabel('Full name (optional)').fill('Test User')
    await page.getByLabel('Email address').fill(uniqueEmail)
    await page.getByLabel('Password', { exact: true }).fill('StrongPass1!')
    await page.getByLabel('Confirm password').fill('StrongPass1!')

    // Submit the form — button text from RegisterPage.tsx
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: account is created — navigated to homepage after success
    // (RegisterPage navigates to '/' on success)
    await expect(page).toHaveURL('/', { timeout: 15000 })
  })

  test('user registers with duplicate email sees error', async ({ page }) => {
    // Entry: user visits the registration page directly
    await page.goto('/register')

    // We rely on a pre-existing seeded user or use a well-known email that
    // already exists from a previous test. We'll try to register twice.
    // First registration with our test email
    const email = `duplicate_${Date.now()}@example.com`

    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('StrongPass1!')
    await page.getByLabel('Confirm password').fill('StrongPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()

    // Wait for redirect to homepage after successful first registration
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Navigate back and attempt to register again with same email
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('StrongPass1!')
    await page.getByLabel('Confirm password').fill('StrongPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: error message shown — text from RegisterPage.tsx line 58
    await expect(
      page.getByText('An account with this email already exists. Please sign in.')
    ).toBeVisible({ timeout: 10000 })
  })

  test('user logs in with correct credentials and is redirected to homepage', async ({ page }) => {
    // Entry: register first so we have valid credentials
    await page.goto('/register')
    const email = `logintest_${Date.now()}@example.com`
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('LoginPass1A!')
    await page.getByLabel('Confirm password').fill('LoginPass1A!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Log out if logged in — look for "Log Out" button in SiteHeader
    const logOutBtn = page.getByRole('button', { name: 'Log out' })
    if (await logOutBtn.isVisible()) {
      await logOutBtn.click()
    }

    // Now go to login page
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // AC: enter correct credentials — labels from LoginPage.tsx
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password').fill('LoginPass1A!')

    // Button text from LoginPage.tsx
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: successfully logged in and redirected to homepage
    await expect(page).toHaveURL('/', { timeout: 15000 })
  })

  test('user enters incorrect credentials and sees error on login page', async ({ page }) => {
    // Entry: login page
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // AC: incorrect credentials
    await page.getByLabel('Email address').fill('nobody@example.com')
    await page.getByLabel('Password').fill('WrongPassword99!')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: error message shown — text from LoginPage.tsx line 41
    await expect(
      page.getByText('Invalid email or password. Please try again.')
    ).toBeVisible({ timeout: 10000 })

    // AC: remains on login page
    await expect(page).toHaveURL('/login')
  })
})
