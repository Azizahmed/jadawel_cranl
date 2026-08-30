export default (client) => ({
  createEndpoint(values, idempotencyKey) {
    return client.post('/arabase/mcp/endpoints/', values, {
      headers: { 'Idempotency-Key': idempotencyKey },
    })
  },
  getPolicy(endpointId) {
    return client.get(`/arabase/mcp/endpoints/${endpointId}/protection-policy/`)
  },
})
