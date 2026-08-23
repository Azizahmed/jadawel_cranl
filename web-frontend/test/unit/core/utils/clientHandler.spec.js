import { getApiBaseUrl } from '@jadawel/modules/core/plugins/clientHandler'

describe('clientHandler API base URL', () => {
  it.each([
    ['https://jadawl.site', 'https://jadawl.site/api'],
    ['https://jadawl.site/', 'https://jadawl.site/api'],
    ['https://jadawl.site////', 'https://jadawl.site/api'],
    ['http://localhost:8000/', 'http://localhost:8000/api'],
    ['', '/api'],
    ['/backend/', '/backend/api'],
  ])('normalizes %s to %s', (backendUrl, expected) => {
    expect(getApiBaseUrl(backendUrl)).toBe(expected)
  })
})
