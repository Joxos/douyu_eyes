import { test, expect } from '@playwright/test'

test('theme toggle persists and applies root data-theme', async ({ page }) => {
  await page.goto('/search')

  const root = page.locator('html')

  await page.getByTestId('theme-dark').click()
  await expect(root).toHaveAttribute('data-theme', 'dark')

  const savedDark = await page.evaluate(() => localStorage.getItem('dy_theme_mode'))
  expect(savedDark).toBe('dark')

  await page.getByTestId('theme-light').click()
  await expect(root).toHaveAttribute('data-theme', 'light')

  const savedLight = await page.evaluate(() => localStorage.getItem('dy_theme_mode'))
  expect(savedLight).toBe('light')

  await page.getByTestId('theme-system').click()
  await expect(root).not.toHaveAttribute('data-theme', /.+/)

  const savedSystem = await page.evaluate(() => localStorage.getItem('dy_theme_mode'))
  expect(savedSystem).toBe('system')
})
