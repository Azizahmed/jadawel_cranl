import addPublicAuthTokenHeader from '@jadawel/modules/database/utils/publicView'

/**
 * The page view's data feed.
 *
 * Not paginated on purpose — the backend caps the response at the view's
 * `row_limit` and reports `truncated` when there was more. A page reads its
 * whole dataset at once, so paging would only push complexity into every
 * AI-authored document.
 */
export default (client) => {
  return {
    /**
     * @param {number|string} viewId The view's id, or its slug on a public page
     *   (the public serializer exposes the slug as the view's id).
     */
    fetchRows({
      viewId,
      search = '',
      searchMode = '',
      publicUrl = false,
      publicAuthToken = null,
      signal = null,
    }) {
      const params = new URLSearchParams()

      if (search) {
        params.append('search', search)
        if (searchMode) {
          params.append('search_mode', searchMode)
        }
      }

      const config = { params }

      if (publicAuthToken) {
        addPublicAuthTokenHeader(config, publicAuthToken)
      }

      if (signal !== null) {
        config.signal = signal
      }

      const suffix = publicUrl ? 'public/rows/' : ''
      return client.get(`/database/views/html-page/${viewId}/${suffix}`, config)
    },
  }
}
