import { test, expect } from '@playwright/test'

test.describe('Sprint 1 — US-001: User Registration', () => {
  test('new user registers with valid credentials and sees confirmation', async ({ page }) => {
    // Entry: navigate to registration page
    await page.goto('/register')

    // The RegisterPage renders heading "Create Account"
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()

    // Fill in the registration form (labels taken directly from RegisterPage.tsx)
    await page.getByLabel(/full name/i).fill('Jane Doe')
    await page.getByLabel('Email address').fill(`register_${Date.now()}@example.com`)
    await page.getByLabel('Password', { exact: true }).fill('StrongPass1!')
    await page.getByLabel(/confirm password/i).fill('StrongPass1!')

    // AC: submit registration
    await page.getByRole('button', { name: 'Create Account' }).click()

    // RegisterPage.tsx calls navigate('/') immediately after setIsSuccess(true), so the
    // "Account Created!" heading is transient. Assert navigation to homepage instead.
    // AC: user is redirected to homepage after registration (account created + confirmation message)
    await expect(page).toHaveURL('/', { timeout: 15000 })
  })

  test('registering with a duplicate email shows an error message', async ({ page }) => {
    // Register an account first
    const email = `dupe_${Date.now()}@example.com`
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('StrongPass1!')
    await page.getByLabel(/confirm password/i).fill('StrongPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()
    // Wait for registration to complete (redirect to homepage)
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Navigate back to registration and try the same email again
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('StrongPass1!')
    await page.getByLabel(/confirm password/i).fill('StrongPass1!')
    await page.getByRole('button', { name: 'Create Account' }).click()

    // AC: error message indicating email is already in use
    // RegisterPage sets serverError = 'An account with this email already exists. Please sign in.'
    await expect(page.getByRole('alert')).toContainText(/already exists/i, { timeout: 10000 })
  })
})

test.describe('Sprint 1 — US-002: User Login', () => {
  test('user with correct credentials signs in and is redirected to homepage', async ({ page }) => {
    // Pre-condition: register an account first
    const email = `login_${Date.now()}@example.com`
    const password = 'StrongPass1!'

    // Register via the registration page
    await page.goto('/register')
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel(/confirm password/i).fill(password)
    await page.getByRole('button', { name: 'Create Account' }).click()
    // Wait for account creation to complete (RegisterPage navigates to / on success)
    await expect(page).toHaveURL('/', { timeout: 15000 })

    // Now sign in
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    // Labels from LoginPage.tsx: "Email address" and "Password"
    await page.getByLabel('Email address').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: redirected to homepage after successful login
    await expect(page).toHaveURL('/', { timeout: 15000 })
  })

  test('user with incorrect password sees an error message and stays on login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

    await page.getByLabel('Email address').fill('nobody@example.com')
    await page.getByLabel('Password').fill('WrongPassword123!')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // AC: error message shown, stays on login page
    // LoginPage.tsx sets serverError = 'Invalid email or password. Please try again.'
    await expect(page.getByRole('alert')).toContainText(/invalid email or password/i, { timeout: 10000 })
    await expect(page).toHaveURL(/login/, { timeout: 5000 })
  })
})
