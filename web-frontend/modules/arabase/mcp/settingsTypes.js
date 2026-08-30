import { MCPEndpointSettingsType } from '@jadawel/modules/core/settingsTypes'
import McpProtectedEndpointSettings from '@jadawel/modules/arabase/mcp/components/McpProtectedEndpointSettings'

export class McpProtectedEndpointSettingsType extends MCPEndpointSettingsType {
  getComponent() {
    return McpProtectedEndpointSettings
  }
}
