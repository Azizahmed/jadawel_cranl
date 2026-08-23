import { expect, vi } from 'vitest'
import { registerRealtimeEvents } from '@jadawel/modules/builder/realtime'

const registerHandlers = () => {
  const handlers = {}
  registerRealtimeEvents({
    registerEvent: (name, handler) => {
      handlers[name] = handler
    },
  })
  return handlers
}

describe('builder realtime events', () => {
  test('ignores a delayed page_created event after its builder is removed', () => {
    const handlers = registerHandlers()
    const store = {
      getters: {
        'application/get': vi.fn(() => undefined),
      },
      dispatch: vi.fn(),
    }

    handlers.page_created(
      { store },
      { page: { id: 2, builder_id: 1, name: 'Delayed page' } }
    )

    expect(store.dispatch).not.toHaveBeenCalled()
  })

  test('adds a page when its builder is still present', () => {
    const handlers = registerHandlers()
    const builder = { id: 1, pages: [] }
    const page = { id: 2, builder_id: 1, name: 'Current page' }
    const store = {
      getters: {
        'application/get': vi.fn(() => builder),
      },
      dispatch: vi.fn(),
    }

    handlers.page_created({ store }, { page })

    expect(store.dispatch).toHaveBeenCalledWith('page/forceCreate', {
      builder,
      page,
    })
  })
})
