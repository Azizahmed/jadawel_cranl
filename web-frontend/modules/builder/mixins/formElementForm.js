import elementForm from '@jadawel/modules/builder/mixins/elementForm'
import { DATA_PROVIDERS_ALLOWED_FORM_ELEMENTS } from '@jadawel/modules/builder/enums'

export default {
  inject: ['workspace', 'builder', 'currentPage', 'elementPage', 'mode'],
  mixins: [elementForm],
  provide() {
    return {
      dataProvidersAllowed: DATA_PROVIDERS_ALLOWED_FORM_ELEMENTS,
    }
  },
}
