import { mountSuspended } from '@nuxt/test-utils/runtime'

import ShareDashboardLink from '@jadawel/modules/arabase/dashboard/components/ShareDashboardLink'

const serviceMocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('@jadawel/modules/arabase/services/dashboardShare', () => ({
  default: () => ({ get: serviceMocks.get }),
}))

describe('ShareDashboardLink', () => {
  beforeEach(() => {
    serviceMocks.get.mockResolvedValue({
      data: { slug: 'public-token', has_password: false },
    })
  })

  it.each(['https://app.jadawl.site', 'https://app.jadawl.site/'])(
    'renders one separator after the configured base URL %s',
    async (baseUrl) => {
      const wrapper = await mountSuspended(ShareDashboardLink, {
        props: { dashboard: { id: 284 } },
        global: {
          mocks: {
            $client: {},
            $config: {
              public: { jadawelEmbeddedShareUrl: baseUrl },
            },
            $router: {
              resolve: () => ({ href: '/public/dashboard/public-token' }),
            },
          },
          stubs: {
            Context: { template: '<div><slot /></div>' },
            DashboardRotateSlugModal: true,
            DashboardSharePasswordModal: true,
            Error: true,
            SwitchInput: true,
            ButtonText: true,
          },
        },
      })

      expect(wrapper.get('.view-sharing__shared-link-box').text()).toBe(
        'https://app.jadawl.site/public/dashboard/public-token'
      )
    }
  )
})
