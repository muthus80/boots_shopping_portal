import { test, expect } from '@playwright/test'

// US-001: User Registration & US-002: User Login

test.describe('Sprint 2 — US-001 & US-002: Registration and Login', () => {
  test('guest registers with valid credentials and sees confirmation', async ({ page }) => {
    // Entry: navigate to the registration page
    await page.goto('/register')

    // AC: registration page loads with Create Account heading
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()

    const uniqueEmail = `e2e_reg_${Date.now()}@example.com`

    // Fill in form fields using labels from RegisterPage.tsx
    await page.getByLabel('Full name (optional)').fill('E2E Test User')
    await page.getByLabel('Email address').fill(uniqueEmail)
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!')
    await page.getByLabel('Confirm password').fill('SecurePass1!')

    // Submit using the 'Create Account' button text from RegisterPage.tsx
    // Wait for network to settle before checking success state
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/v1/auth/register'), { timeout: 15000 }),
      page.getByRole('button', { name: 'Create Account' }).click(),
    ])

    // AC: account created — success state shows "Account Created!" heading (RegisterPage.tsx)
    // OR redirect to homepage (navigate('/') in RegisterPage.tsx onSubmit success)
    // Give adequate time for the React state transition or navigation
    const successHeading = page.getByRole('heading', { name: 'Account Created!' })
    const homeHeading = page.getByRole('heading', { name: 'Step Into Style' })
    await expect(successHeading.or(homeHeading)).toBeVisible({ timeout: 15000 })
  })

  test('guest tries to register with duplicate email and sees error', async ({ page }) => {
    // First create an account
    const duplicateEmail = `e2e_dup_${Date.now()}@example.com`
    await page.goto('/register')
    await page.getByLabel('Email address').fill(duplicateEmail)
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!')
    await page.getByLabel('Confirm password').fill('SecurePass1!')
    // Wait for first register to complete before attempting duplicate
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/v1/auth/register'), { timeout: 15000 }),
      page.getByRole('button', { name: 'Create Account' }).click(),
    ])
    // Wait for redirect to home (first registration succeeds)
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Try again with same email
    await page.goto('/register')
    await page.getByLabel('Email address').fill(duplicateEmail)
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!')
    await page.getByLabel('Confirm password').fill('SecurePass1!')
    // Wait for second register API call (should return 409)
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/v1/auth/register'), { timeout: 15000 }),
      page.getByRole('button', { name: 'Create Account' }).click(),
    ])

    // AC: error message displayed for duplicate email (div role="alert" in RegisterPage.tsx)
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 })
  })

  test('user logs in with correct credentials and is redirected to homepage', async ({ page }) => {
    // Register first so we have valid credentials
    const email = `e2e_login_${Date.now()}@example.com`
    const password = 'SecurePass1!'

    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    // Wait for register API response before proceeding
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/v1/auth/register'), { timeout: 15000 }),
      page.getByRole('button', { name: 'Create Account' }).click(),
    ])

    // Wait for redirect to home after registration
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Now go to login
    await page.goto('/login')

    // AC: login page loads with Sign In heading (LoginPage.tsx)
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // Fill in credentials using exact labels from LoginPage.tsx
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password').fill(password)

    // Wait for login API response
    const [loginResp] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/v1/auth/login'), { timeout: 15000 }),
      page.getByRole('button', { name: 'Sign In' }).click(),
    ])

    // AC: redirected to homepage after successful login
    await expect(page).toHaveURL('/', { timeout: 10000 })
    // Homepage heading is "Step Into Style" (HomePage.tsx)
    await expect(page.getByRole('heading', { name: 'Step Into Style' })).toBeVisible()
  })

  test('user logs in with incorrect password sees error and stays on login page', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel('Email address').fill('nonexistent@example.com')
    await page.getByLabel('Password').fill('WrongPassword99')

    // Wait for login API to respond (should return 401) before checking for error alert
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/v1/auth/login'), { timeout: 15000 }),
      page.getByRole('button', { name: 'Sign In' }).click(),
    ])

    // AC: error message displayed (LoginPage.tsx renders div role="alert" on 401)
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 })
    // AC: user remains on login page
    await expect(page).toHaveURL(/login/)
  })
})
