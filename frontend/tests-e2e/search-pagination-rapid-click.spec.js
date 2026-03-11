import { test, expect } from '@playwright/test'

test('rapid clicks on pagination do not break page indicator or select button text', async ({ page }) => {
  await page.goto('/search')

  await page.getByTestId('search-input').fill('比赛')
  await page.getByTestId('search-submit').click()

  const nextBtn = page.getByRole('button', { name: 'Next' })
  const prevBtn = page.getByRole('button', { name: 'Previous' })
  const pageInfo = page.locator('.page-info')

  await expect(pageInfo).toContainText('第')

  if (await nextBtn.isEnabled()) {
    await nextBtn.click({ clickCount: 2 })
    await page.waitForTimeout(300)
    await expect(prevBtn).toBeEnabled()
  }

  const selectedText = await page.evaluate(() => window.getSelection()?.toString() ?? '')
  expect(selectedText.trim()).toBe('')

  await expect(pageInfo).not.toHaveText('第 1 / 1 页（共 0 条）')
})
