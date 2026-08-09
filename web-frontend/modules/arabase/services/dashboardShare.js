import addPublicAuthTokenHeader from '@jadawel/modules/database/utils/publicView'

/**
 * The public link of a dashboard — the dashboard equivalent of sharing a form
 * or grid view. Owner endpoints live under `/arabase/dashboard/<id>/share/`,
 * the anonymous ones under `/arabase/public/dashboard/<slug>/`.
 */
export default (client) => {
  return {
    get(dashboardId) {
      return client.get(`/arabase/dashboard/${dashboardId}/share/`)
    },
    create(dashboardId) {
      return client.post(`/arabase/dashboard/${dashboardId}/share/`)
    },
    delete(dashboardId) {
      return client.delete(`/arabase/dashboard/${dashboardId}/share/`)
    },
    rotateSlug(dashboardId) {
      return client.post(`/arabase/dashboard/${dashboardId}/share/rotate-slug/`)
    },
    setPassword(dashboardId, password) {
      return client.patch(`/arabase/dashboard/${dashboardId}/share/password/`, {
        password,
      })
    },
    fetchPublicInfo(slug, publicAuthToken = null) {
      const config = {}
      if (publicAuthToken) {
        addPublicAuthTokenHeader(config, publicAuthToken)
      }
      return client.get(`/arabase/public/dashboard/${slug}/`, config)
    },
    dispatchPublicDataSource(slug, dataSourceId, publicAuthToken = null) {
      const config = {}
      if (publicAuthToken) {
        addPublicAuthTokenHeader(config, publicAuthToken)
      }
      return client.post(
        `/arabase/public/dashboard/${slug}/dispatch/${dataSourceId}/`,
        {},
        config
      )
    },
    authenticate(slug, password) {
      return client.post(`/arabase/public/dashboard/${slug}/auth/`, {
        password,
      })
    },
  }
}
