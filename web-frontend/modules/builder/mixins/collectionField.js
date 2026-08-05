import element from '@jadawel/modules/builder/mixins/element'
import { resolveColor } from '@jadawel/modules/core/utils/colors'
import { ThemeConfigBlockType } from '@jadawel/modules/builder/themeConfigBlockTypes'
import applicationContextMixin from '@jadawel/modules/builder/mixins/applicationContext'

export default {
  inject: ['workspace', 'builder', 'elementPage', 'mode'],
  mixins: [element, applicationContextMixin],
  props: {
    element: {
      type: Object,
      required: true,
    },
    field: {
      type: Object,
      required: true,
    },
  },
  computed: {
    elementType() {
      return this.$registry.get('element', this.element.type)
    },
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
