import { test, expect } from '@playwright/test'

test('search sort=count and sort=last_seen return different ordering', async ({ page }) => {
  const searchRequestUrls = []
  await page.route('**/api/search**', async (route) => {
    const url = route.request().url()
    const isLastSeen = url.includes('sort=last_seen')
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            content: '比赛开始',
            count: 12,
            last_seen_at: isLastSeen ? '2026-03-11T10:00:00Z' : '2026-03-11T09:00:00Z',
          },
        ],
        limit: 20,
        offset: 0,
        total: 1,
        total_pages: 1,
        current_page: 1,
      }),
    })
  })

  page.on('requestfinished', (request) => {
    const url = request.url()
    if (url.includes('/api/search?')) {
      searchRequestUrls.push(url)
    }
  })

  await page.goto('/search')

  const input = page.getByTestId('search-input')
  const submit = page.getByTestId('search-submit')
  const sortSelect = page.locator('select.sort-select')

  await input.fill('比赛')

  await sortSelect.selectOption('count')
  await submit.click()
  await expect(page.getByTestId('search-results')).toBeVisible()
  await expect(page.locator('.search-result-count').first()).toContainText('出现次数：')

  await sortSelect.selectOption('last_seen')
  await submit.click()
  await expect(page.getByTestId('search-results')).toBeVisible()
  const lastSeenLabel = page.getByTestId('last-seen-0')
  await expect(lastSeenLabel).toContainText('最后出现时间：')
  await expect(lastSeenLabel).not.toContainText('最后出现时间：—')
  await expect(lastSeenLabel).not.toContainText('最后出现时间：未知')
  await expect(lastSeenLabel).toContainText(/\d{4}/)

  expect(searchRequestUrls.some((u) => u.includes('sort=count'))).toBeTruthy()
  expect(searchRequestUrls.some((u) => u.includes('sort=last_seen'))).toBeTruthy()
})
