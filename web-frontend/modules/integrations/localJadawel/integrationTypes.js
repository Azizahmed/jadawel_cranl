import { IntegrationType } from '@jadawel/modules/core/integrationTypes'
import LocalJadawelForm from '@jadawel/modules/integrations/localJadawel/components/integrations/LocalJadawelForm'
import localJadawelIntegration from '@jadawel/modules/integrations/localJadawel/assets/images/localJadawelIntegration.svg?url'

export class LocalJadawelIntegrationType extends IntegrationType {
  static getType() {
    return 'local_jadawel'
  }

  get name() {
    return this.app.$i18n.t('integrationType.localJadawel')
  }

  get image() {
    return localJadawelIntegration
  }

  getSummary(integration) {
    if (!integration.authorized_user) {
      return this.app.$i18n.t('localJadawelIntegrationType.localJadawelNoUser')
    }

    return this.app.$i18n.t('localJadawelIntegrationType.localJadawelSummary', {
      name: integration.authorized_user.first_name,
      username: integration.authorized_user.username,
    })
  }

  get formComponent() {
    return LocalJadawelForm
  }

  get warning() {
    return this.app.$i18n.t('localJadawelIntegrationType.localJadawelWarning')
  }

  getDefaultValues() {
    const user = this.app.$store.getters['auth/getUserObject']
    return {
      authorized_user: { username: user.username, first_name: user.first_name },
    }
  }

  getOrder() {
    return 10
  }
}
