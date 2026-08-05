import lowercase from '@jadawel/modules/core/filters/lowercase'
import nameAbbreviation from '@jadawel/modules/core/filters/nameAbbreviation'
import uppercase from '@jadawel/modules/core/filters/uppercase'

export default defineNuxtPlugin((nuxtApp) => {
  return {
    provide: {
      filters: {
        lowercase,
        uppercase,
        nameAbbreviation,
      },
    },
  }
})
