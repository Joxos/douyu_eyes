import { test, expect } from '@playwright/test'

test('search results show count and provide one-click copy button', async ({ page }) => {
  await page.route('**/api/search**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          { content: '比赛开始', count: 12, last_seen_at: '2026-03-11T09:30:00Z' },
          { content: '加油', count: 7, last_seen_at: '2026-03-11T09:29:00Z' },
        ],
        limit: 20,
        offset: 0,
        total: 2,
        total_pages: 1,
        current_page: 1,
      }),
    })
  })

  await page.goto('/search')

  await page.getByTestId('search-input').fill('比赛')
  await page.getByTestId('search-submit').click()

  const results = page.getByTestId('search-results')
  await expect(results).toBeVisible()

  const firstCountLabel = page.locator('.search-result-count').first()
  await expect(firstCountLabel).toContainText('出现次数：')

  const copyBtn = page.getByTestId('copy-result-0')
  await expect(copyBtn).toBeVisible()

  await page.evaluate(() => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText = (text) => {
        window.__copiedText = text
        return Promise.resolve()
      }
    }
  })

  const firstContent = (await page.locator('.search-result-content').first().innerText()).trim()
  await copyBtn.click()

  const toastHost = page.getByTestId('toast-host')
  await expect(toastHost).toBeVisible()
  const toastMessage = page.getByTestId('toast-message').last()
  await expect(toastMessage).toContainText('复制成功')
  await expect(toastMessage).toHaveAttribute('role', 'status')

  const copiedText = await page.evaluate(() => window.__copiedText ?? '')
  expect(copiedText).toBe(firstContent)
})
