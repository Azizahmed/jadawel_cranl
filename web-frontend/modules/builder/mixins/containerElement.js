import element from '@jadawel/modules/builder/mixins/element'
import { DIRECTIONS } from '@jadawel/modules/builder/enums'

export default {
  mixins: [element],
  computed: {
    DIRECTIONS: () => DIRECTIONS,
    children() {
      return this.$store.getters['element/getChildren'](
        this.elementPage,
        this.element
      )
    },
  },
}
