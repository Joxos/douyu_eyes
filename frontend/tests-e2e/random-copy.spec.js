import { test, expect } from '@playwright/test'

test('random page provides one-click copy and shows toast', async ({ page }) => {
  await page.route('**/api/random', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        content: '比赛开始',
        count: 12,
        last_seen_at: '2026-03-11T10:00:00Z',
      }),
    })
  })

  await page.goto('/random')

  const result = page.getByTestId('random-content')
  await expect(result).toBeVisible()
  await expect(page.getByTestId('random-meta-count')).toContainText('被刷次数：12')
  const lastSeen = page.getByTestId('random-meta-last-seen')
  await expect(lastSeen).toContainText('最后出现时间：')
  await expect(lastSeen).toContainText(/\d{4}/)

  await page.evaluate(() => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText = (text) => {
        window.__copiedText = text
        return Promise.resolve()
      }
    }
  })

  const copyButton = page.getByTestId('copy-random')
  await expect(copyButton).toBeVisible()
  await copyButton.click()

  const toastHost = page.getByTestId('toast-host')
  await expect(toastHost).toBeVisible()
  const toastMessage = page.getByTestId('toast-message').last()
  await expect(toastMessage).toContainText('复制成功')
  await expect(toastMessage).toHaveAttribute('role', 'status')

  const copiedText = await page.evaluate(() => window.__copiedText ?? '')
  expect(copiedText).toBe('比赛开始')
})
