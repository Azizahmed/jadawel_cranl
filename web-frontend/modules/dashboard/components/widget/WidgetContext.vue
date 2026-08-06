<template>
  <Context ref="context" overflow-scroll max-height-if-outside-viewport>
    <ul class="context__menu">
      <li v-if="canBeUpdated" class="context__menu-item">
        <a
          ref="sizeLink"
          class="context__menu-item-link"
          @click="$refs.sizeContext.toggle($refs.sizeLink, 'bottom', 'left', 0)"
        >
          <i class="context__menu-item-icon iconoir-expand"></i>
          {{ $t('widgetContext.size') }}
        </a>
        <WidgetSizeContext
          ref="sizeContext"
          :widget="widget"
          :dashboard="dashboard"
          @selected="hide()"
        ></WidgetSizeContext>
      </li>
      <li v-if="canBeDeleted" class="context__menu-item">
        <a
          class="context__menu-item-link context__menu-item-link--delete"
          :class="{ 'context__menu-item-link--loading': isDeleteInProgress }"
          @click="deleteWidget()"
        >
          <i class="context__menu-item-icon iconoir-bin"></i>
          {{ $t('widgetContext.delete') }}
        </a>
      </li>
    </ul>
  </Context>
</template>

<script>
import context from '@jadawel/modules/core/mixins/context'
import { notifyIf } from '@jadawel/modules/core/utils/error'
import WidgetSizeContext from '@jadawel/modules/arabase/dashboard/components/widget/WidgetSizeContext'

export default {
  name: 'WidgetContext',
  components: { WidgetSizeContext },
  mixins: [context],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    widget: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      isDeleteInProgress: false,
    }
  },
  computed: {
    canBeDeleted() {
      return this.$hasPermission(
        'dashboard.widget.delete',
        this.widget,
        this.dashboard.workspace.id
      )
    },
    canBeUpdated() {
      return this.$hasPermission(
        'dashboard.widget.update',
        this.widget,
        this.dashboard.workspace.id
      )
    },
  },
  methods: {
    async deleteWidget() {
      this.isDeleteInProgress = true
      try {
        await this.$store.dispatch(
          'dashboardApplication/deleteWidget',
          this.widget.id
        )
      } catch (error) {
        notifyIf(error, 'dashboard')
      }
      this.isDeleteInProgress = false
      if (this.$refs.context) {
        this.hide()
      }
    },
  },
}
</script>
