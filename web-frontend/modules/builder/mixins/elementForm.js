import { resolveColor } from '@jadawel/modules/core/utils/colors'
import { ThemeConfigBlockType } from '@jadawel/modules/builder/themeConfigBlockTypes'
import form from '@jadawel/modules/core/mixins/form'

export default {
  inject: ['workspace', 'builder', 'currentPage', 'elementPage', 'mode'],
  mixins: [form],
  computed: {
    themeConfigBlocks() {
      return this.$registry.getOrderedList('themeConfigBlock')
    },
    colorVariables() {
      return ThemeConfigBlockType.getAllColorVariables(
        this.themeConfigBlocks,
        this.builder.theme
      )
    },
  },
  methods: {
    resolveColor,
  },
}
