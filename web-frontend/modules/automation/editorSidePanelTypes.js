import { Registerable } from '@jadawel/modules/core/registry'
import NodeSidePanel from '@jadawel/modules/automation/components/workflow/sidePanels/NodeSidePanel'
import HistorySidePanel from '@jadawel/modules/automation/components/workflow/sidePanels/HistorySidePanel'

export class editorSidePanelType extends Registerable {
  get component() {
    return null
  }

  get guidedTourAttr() {
    return ''
  }

  isDeactivated() {
    return false
  }

  getOrder() {
    return this.order
  }
}

export class NodeEditorSidePanelType extends editorSidePanelType {
  static getType() {
    return 'node'
  }

  get guidedTourAttr() {
    return 'automation-node-sidepanel'
  }

  get component() {
    return NodeSidePanel
  }

  getOrder() {
    return 10
  }
}

export class HistoryEditorSidePanelType extends editorSidePanelType {
  static getType() {
    return 'history'
  }

  get guidedTourAttr() {
    return 'automation-history-sidepanel'
  }

  get component() {
    return HistorySidePanel
  }

  getOrder() {
    return 20
  }
}
