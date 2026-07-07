import { test, expect } from '@playwright/test'

/**
 * Sprint 1 – US-001: User Registration & US-002: User Login
 *
 * Page text sourced directly from:
 *   frontend/src/pages/RegisterPage.tsx  (heading: "Create Account", button: "Create Account")
 *   frontend/src/pages/LoginPage.tsx     (heading: "Sign In", button: "Sign In")
 */

test.describe('Sprint 1 — US-001: User Registration', () => {
  test('user registers with valid credentials and sees confirmation', async ({ page }) => {
    // Entry: navigate to the registration page
    await page.goto('/register')

    // AC: registration page renders its heading
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()

    const uniqueEmail = `qa_test_${Date.now()}@example.com`

    // Fill in the registration form (labels sourced from RegisterPage.tsx)
    await page.getByLabel(/full name/i).fill('QA Tester')
    await page.getByLabel('Email address').fill(uniqueEmail)
    await page.getByLabel('Password', { exact: true }).fill('TestPass1!')
    await page.getByLabel('Confirm password').fill('TestPass1!')

    // Submit
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: account created — page navigates away (to / or shows success)
    // The component navigates to '/' after successful registration
    await expect(page).toHaveURL('/', { timeout: 15000 })
  })

  test('registering with an existing email shows an error', async ({ page }) => {
    // First registration
    await page.goto('/register')
    const email = `duplicate_${Date.now()}@example.com`
    await page.getByLabel(/full name/i).fill('First User')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('TestPass1!')
    await page.getByLabel('Confirm password').fill('TestPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Second registration with same email
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('TestPass1!')
    await page.getByLabel('Confirm password').fill('TestPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: error message indicating email is already in use
    // RegisterPage.tsx renders: "An account with this email already exists. Please sign in."
    await expect(page.getByRole('alert')).toContainText(/already exists/i, { timeout: 10000 })
  })
})

test.describe('Sprint 1 — US-002: User Login', () => {
  test('user logs in with correct credentials and is redirected to homepage', async ({ page }) => {
    // Register a user first so we can log in
    await page.goto('/register')
    const email = `login_test_${Date.now()}@example.com`
    const password = 'LoginTest1!'
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    await page.getByRole('button', { name: 'Create Account' }).click()
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Log out first (if header shows "Log Out")
    // Navigate directly to login page
    await page.goto('/login')

    // AC: login page renders its heading (LoginPage.tsx: h1 "Sign In")
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // Fill in credentials
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: redirected to homepage on success
    await expect(page).toHaveURL('/', { timeout: 15000 })
  })

  test('login with incorrect credentials shows an error and stays on login page', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel('Email address').fill('nobody@example.com')
    await page.getByLabel('Password').fill('WrongPassword99!')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: error message shown (LoginPage.tsx: "Invalid email or password. Please try again.")
    await expect(page.getByRole('alert')).toContainText(/invalid email or password/i, { timeout: 10000 })

    // AC: remain on login page
    await expect(page).toHaveURL(/login/, { timeout: 5000 })
  })
})
