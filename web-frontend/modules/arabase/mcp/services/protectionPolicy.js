export default (client) => ({
  fetchPolicy(endpointId) {
    return client.get(`/arabase/mcp/endpoints/${endpointId}/protection-policy/`)
  },
  createEndpoint(values, idempotencyKey) {
    return client.post('/arabase/mcp/endpoints/', values, {
      headers: { 'Idempotency-Key': idempotencyKey },
    })
  },
  replacePolicy(endpointId, values, idempotencyKey) {
    return client.patch(
      `/arabase/mcp/endpoints/${endpointId}/protection-policy/`,
      values,
      { headers: { 'Idempotency-Key': idempotencyKey } }
    )
  },
  reactivatePolicy(endpointId, expectedRevision) {
    return client.post(
      `/arabase/mcp/endpoints/${endpointId}/protection-policy/`,
      { expected_revision: expectedRevision }
    )
  },
})
