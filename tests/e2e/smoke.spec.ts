import { test, expect } from '@playwright/test'

test('app is reachable', async ({ page }) => {
  const response = await page.goto('/')
  expect(response?.status()).toBeLessThan(400)
})
