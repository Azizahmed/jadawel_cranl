export default (client) => ({
  createEndpoint(values, idempotencyKey) {
    return client.post('/arabase/mcp/endpoints/', values, {
      headers: { 'Idempotency-Key': idempotencyKey },
    })
  },
})
