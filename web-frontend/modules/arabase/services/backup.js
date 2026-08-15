export default (client) => {
  return {
    /** Enabled state, schedule and health in one call, for the first paint. */
    fetchOverview() {
      return client.get('/arabase/admin/backup/')
    },
    setFrequency(frequency) {
      return client.patch('/arabase/admin/backup/', { frequency })
    },
    fetchRuns() {
      return client.get('/arabase/admin/backup/runs/')
    },
    runNow() {
      return client.post('/arabase/admin/backup/run/')
    },
    /**
     * Restores into a database the operator nominates. The backend refuses the
     * live one — this never overwrites production.
     */
    restore(key, targetDatabaseUrl) {
      return client.post('/arabase/admin/backup/restore/', {
        key,
        target_database_url: targetDatabaseUrl,
      })
    },
  }
}
