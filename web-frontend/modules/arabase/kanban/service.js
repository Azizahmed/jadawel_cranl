/**
 * The kanban board's data feed: the stacks (one per select option of the
 * view's grouping field, plus the stack of rows without a value) and one
 * page of rows per stack.
 */
export default (client) => {
  return {
    fetchBoard({ viewId, search = '' }) {
      const config = { params: {} }
      if (search) {
        config.params.search = search
      }
      return client.get(`/database/views/kanban/${viewId}/`, config)
    },
    fetchStackRows({ viewId, stackId, offset = 0, limit = 40, search = '' }) {
      const config = {
        params: {
          offset,
          limit,
        },
      }
      if (search) {
        config.params.search = search
      }
      return client.get(
        `/database/views/kanban/${viewId}/stacks/${stackId}/`,
        config
      )
    },
  }
}
