import McpEndpoint from '@jadawel/modules/core/components/settings/McpEndpoint'
import { TestApp } from '@jadawel/test/helpers/testApp'

const ENDPOINT_URL = 'https://api.example.test/mcp/secret-key/sse'

const translations = {
  'mcpEndpoint.codexInstructions':
    'Run the command below, then run `codex mcp list`.',
  'mcpEndpoint.otherClientsTitle': 'Others',
  'mcpEndpoint.otherClientsInstructions':
    'Copy the prompt below and give it to any AI agent.',
  'mcpEndpoint.otherClientsPrompt':
    'Set up the following Jadawel MCP server.\nServer URL: {endpointUrl}\nTreat this URL as a password.',
}

const getTranslation = (key, values = {}) => {
  const value = translations[key] ?? key
  return Object.entries(values).reduce(
    (translated, [name, replacement]) =>
      translated.replaceAll(`{${name}}`, replacement),
    value
  )
}

describe('McpEndpoint setup instructions', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
    testApp.store.dispatch('workspace/forceCreate', {
      id: 7,
      name: 'Operations',
    })
  })

  afterEach(async () => {
    await testApp.afterEach()
  })

  const mountComponent = async () =>
    await testApp.mount(McpEndpoint, {
      props: {
        endpoint: {
          id: 4,
          key: 'secret-key',
          name: 'Jadawel MCP',
          workspace_id: 7,
        },
      },
      global: {
        mocks: {
          $config: {
            public: { publicBackendUrl: 'https://api.example.test' },
          },
          $t: getTranslation,
        },
      },
    })

  test('offers Codex and a reusable prompt instead of Windsurf', async () => {
    const wrapper = await mountComponent()
    await wrapper.get('.mcp-endpoint__toggle a').trigger('click')
    await wrapper.get('.flex > a').trigger('click')

    const tabLabels = wrapper
      .findAll('.tabs__link')
      .map((tab) => tab.text().trim())

    expect(tabLabels).toStrictEqual(['Claude', 'Cursor', 'Codex', 'Others'])
    expect(wrapper.text()).not.toContain('Windsurf')

    await wrapper.findAll('.tabs__item')[2].trigger('click')
    expect(wrapper.get('.tab').text()).toContain(
      `codex mcp add jadawel -- npx -y mcp-remote "${ENDPOINT_URL}"`
    )
    expect(wrapper.get('.tab').text()).toContain('codex mcp list')

    await wrapper.findAll('.tabs__item')[3].trigger('click')
    const otherPrompt = wrapper.get('.tab').text()
    expect(otherPrompt).toContain('Set up the following Jadawel MCP server')
    expect(otherPrompt).toContain(`Server URL: ${ENDPOINT_URL}`)
    expect(otherPrompt).toContain('Treat this URL as a password')
  })
})
