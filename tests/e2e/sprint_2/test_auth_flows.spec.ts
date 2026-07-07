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
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: account created — success state shows "Account Created!" heading (RegisterPage.tsx)
    // OR redirect to homepage — either means success
    const successHeading = page.getByRole('heading', { name: 'Account Created!' })
    const homeHeading = page.getByRole('heading', { name: 'Step Into Style' })
    await expect(successHeading.or(homeHeading)).toBeVisible({ timeout: 10000 })
  })

  test('guest tries to register with duplicate email and sees error', async ({ page }) => {
    // First create an account
    const duplicateEmail = `e2e_dup_${Date.now()}@example.com`
    await page.goto('/register')
    await page.getByLabel('Email address').fill(duplicateEmail)
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!')
    await page.getByLabel('Confirm password').fill('SecurePass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()

    // Wait for navigation or success
    await page.waitForTimeout(2000)

    // Try again with same email
    await page.goto('/register')
    await page.getByLabel('Email address').fill(duplicateEmail)
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!')
    await page.getByLabel('Confirm password').fill('SecurePass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: error message displayed for duplicate email (role="alert" in RegisterPage.tsx)
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
    await page.getByRole('button', { name: 'Create Account' }).click()
    await page.waitForTimeout(2000)

    // Now go to login
    await page.goto('/login')

    // AC: login page loads with Sign In heading (LoginPage.tsx)
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // Fill in credentials using exact labels from LoginPage.tsx
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: redirected to homepage after successful login
    await expect(page).toHaveURL('/', { timeout: 10000 })
    // Homepage heading is "Step Into Style" (HomePage.tsx)
    await expect(page.getByRole('heading', { name: 'Step Into Style' })).toBeVisible()
  })

  test('user logs in with incorrect password sees error and stays on login page', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel('Email address').fill('nonexistent@example.com')
    await page.getByLabel('Password').fill('WrongPassword99')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: error message displayed (role="alert" in LoginPage.tsx)
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 })
    // AC: user remains on login page
    await expect(page).toHaveURL(/login/)
  })
})
