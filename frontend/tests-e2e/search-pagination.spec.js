import { test, expect } from '@playwright/test'

test('search pagination metadata and button state are usable', async ({ page }) => {
  await page.goto('/search')

  await page.getByTestId('search-input').fill('比赛')
  await page.getByTestId('search-submit').click()

  const pageInfo = page.locator('.page-info')
  await expect(pageInfo).toContainText('第')
  await expect(pageInfo).toContainText('页（共')

  const pageText = await pageInfo.innerText()
  expect(pageText).not.toBe('第 1 / 1 页（共 0 条）')

  const nextBtn = page.getByRole('button', { name: '下一页' })
  const prevBtn = page.getByRole('button', { name: '上一页' })

  if (await nextBtn.isEnabled()) {
    await nextBtn.click()
    await expect(prevBtn).toBeEnabled()
    await expect(pageInfo).not.toHaveText('第 1 / 1 页（共 0 条）')
  }
})
