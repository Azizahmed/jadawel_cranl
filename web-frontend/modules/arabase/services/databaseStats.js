/**
 * Table / field / row counters for the databases on the workspace home page.
 *
 * Served by the fork's own `arabase` API prefix rather than folded into the
 * application payload: that payload is fetched on every route (the sidebar needs
 * it) while these counters are only read by one page, and row counting is the
 * expensive part. See `arabase/api/database_stats.py`.
 */
export default (client) => {
  return {
    /**
     * Returns an object keyed by database id:
     * `{ [id]: { table_count, field_count, row_count, rows_exact } }`.
     *
     * `row_count` is null and `rows_exact` false when the workspace holds more
     * tables than the endpoint counts in a single pass.
     */
    fetchAll(workspaceId) {
      return client.get(`/arabase/workspace/${workspaceId}/database-stats/`)
    },
  }
}
