/**
 * Rows created per day across a workspace, for the home page activity chart.
 *
 * Separate call from `databaseStats` even though both walk the same tables: the
 * counters decorate cards that are on screen immediately, while this feeds one
 * chart further down the page. Keeping them apart means a workspace large enough
 * to make the activity query slow still gets its card numbers promptly.
 * See `arabase/api/activity.py`.
 */
export default (client) => {
  return {
    /**
     * Returns `{ days, complete, total, series: [{ date, count }] }`.
     *
     * The series is dense — quiet days are present with a count of zero — and
     * ordered oldest first. `complete` is false and `series` empty when the
     * workspace holds more tables than the endpoint scans in one pass.
     */
    fetch(workspaceId, days = 30) {
      return client.get(`/arabase/workspace/${workspaceId}/activity/`, {
        params: { days },
      })
    },
  }
}
