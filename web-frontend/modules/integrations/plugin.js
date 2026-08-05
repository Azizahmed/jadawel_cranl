import { defineNuxtPlugin } from '#app'

import { LocalBaserowIntegrationType } from '@jadawel/modules/integrations/localBaserow/integrationTypes'
import { SMTPIntegrationType } from '@jadawel/modules/integrations/core/integrationTypes'
import { AIIntegrationType } from '@jadawel/modules/integrations/ai/integrationTypes'
import {
  LocalBaserowGetRowServiceType,
  LocalBaserowListRowsServiceType,
  LocalBaserowAggregateRowsServiceType,
  LocalBaserowCreateRowWorkflowServiceType,
  LocalBaserowDeleteRowWorkflowServiceType,
  LocalBaserowUpdateRowWorkflowServiceType,
  LocalBaserowRowsCreatedTriggerServiceType,
  LocalBaserowRowsUpdatedTriggerServiceType,
  LocalBaserowRowsDeletedTriggerServiceType,
} from '@jadawel/modules/integrations/localBaserow/serviceTypes'
import {
  CoreHTTPRequestServiceType,
  PeriodicTriggerServiceType,
  CoreRouterServiceType,
  CoreSMTPEmailServiceType,
  CoreHTTPTriggerServiceType,
  CoreIteratorServiceType,
} from '@jadawel/modules/integrations/core/serviceTypes'
import { AIAgentServiceType } from '@jadawel/modules/integrations/ai/serviceTypes'
import { SlackWriteMessageServiceType } from '@jadawel/modules/integrations/slack/serviceTypes'
import { SlackBotIntegrationType } from '@jadawel/modules/integrations/slack/integrationTypes'

export default defineNuxtPlugin({
  dependsOn: ['core'],
  setup(nuxtApp) {
    const { $registry } = nuxtApp

    const context = { app: nuxtApp }

    $registry.register('integration', new LocalBaserowIntegrationType(context))
    $registry.register('integration', new SMTPIntegrationType(context))
    $registry.register('integration', new AIIntegrationType(context))
    $registry.register('integration', new SlackBotIntegrationType(context))

    $registry.register('service', new LocalBaserowGetRowServiceType(context))
    $registry.register('service', new LocalBaserowListRowsServiceType(context))
    $registry.register(
      'service',
      new LocalBaserowAggregateRowsServiceType(context)
    )
    $registry.register(
      'service',
      new LocalBaserowCreateRowWorkflowServiceType(context)
    )
    $registry.register(
      'service',
      new LocalBaserowUpdateRowWorkflowServiceType(context)
    )
    $registry.register(
      'service',
      new LocalBaserowDeleteRowWorkflowServiceType(context)
    )
    $registry.register('service', new CoreHTTPRequestServiceType(context))
    $registry.register('service', new CoreSMTPEmailServiceType(context))
    $registry.register('service', new CoreRouterServiceType(context))
    $registry.register('service', new CoreHTTPTriggerServiceType(context))
    $registry.register('service', new CoreIteratorServiceType(context))
    $registry.register('service', new AIAgentServiceType(context))
    $registry.register('service', new PeriodicTriggerServiceType(context))
    $registry.register('service', new SlackWriteMessageServiceType(context))
    $registry.register(
      'service',
      new LocalBaserowRowsCreatedTriggerServiceType(context)
    )
    $registry.register(
      'service',
      new LocalBaserowRowsUpdatedTriggerServiceType(context)
    )
    $registry.register(
      'service',
      new LocalBaserowRowsDeletedTriggerServiceType(context)
    )
  },
})
