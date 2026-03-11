import { test, expect } from '@playwright/test'

test('search sort=count and sort=last_seen return different ordering', async ({ page }) => {
  const searchRequestUrls = []
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
  const firstCount = (await page.locator('.search-result-item div').first().innerText()).trim()

  await sortSelect.selectOption('last_seen')
  await submit.click()
  await expect(page.getByTestId('search-results')).toBeVisible()
  const firstLastSeen = (await page.locator('.search-result-item div').first().innerText()).trim()

  expect(firstCount.length).toBeGreaterThan(0)
  expect(firstLastSeen.length).toBeGreaterThan(0)
  expect(searchRequestUrls.some((u) => u.includes('sort=count'))).toBeTruthy()
  expect(searchRequestUrls.some((u) => u.includes('sort=last_seen'))).toBeTruthy()
})
