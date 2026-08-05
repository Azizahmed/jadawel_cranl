<template>
  <div>
    <form class="margin-bottom-2" @submit.prevent>
      <FormSection :title="$t('progressWidgetSettings.target')">
        <FormGroup
          :label="$t('progressWidgetSettings.targetValue')"
          :error="targetInvalid"
          class="margin-bottom-2"
          small-label
          required
          horizontal
          horizontal-narrow
        >
          <FormInput
            v-model="target"
            type="number"
            :error="targetInvalid"
            @blur="commitTarget"
            @keydown.enter.prevent="commitTarget"
          />
          <template #error>
            {{ $t('progressWidgetSettings.targetError') }}
          </template>
        </FormGroup>

        <FormGroup
          :label="$t('progressWidgetSettings.displayStyle')"
          class="margin-bottom-2"
          small-label
          required
          horizontal
          horizontal-narrow
        >
          <Dropdown v-model="displayStyle">
            <DropdownItem
              :name="$t('progressWidgetSettings.bar')"
              value="bar"
              icon="iconoir-minus"
            ></DropdownItem>
            <DropdownItem
              :name="$t('progressWidgetSettings.ring')"
              value="ring"
              icon="iconoir-circle"
            ></DropdownItem>
          </Dropdown>
        </FormGroup>

        <FormGroup
          :label="$t('progressWidgetSettings.warningThreshold')"
          :helper-text="$t('progressWidgetSettings.thresholdHelp')"
          class="margin-bottom-2"
          small-label
          horizontal
          horizontal-narrow
        >
          <FormInput
            v-model="warningThreshold"
            type="number"
            :min="0"
            :max="100"
            @blur="commitThresholds"
            @keydown.enter.prevent="commitThresholds"
          />
        </FormGroup>

        <FormGroup
          :label="$t('progressWidgetSettings.successThreshold')"
          :error="thresholdsInvalid"
          small-label
          horizontal
          horizontal-narrow
        >
          <FormInput
            v-model="successThreshold"
            type="number"
            :min="0"
            :max="100"
            :error="thresholdsInvalid"
            @blur="commitThresholds"
            @keydown.enter.prevent="commitThresholds"
          />
          <template #error>
            {{ $t('progressWidgetSettings.thresholdError') }}
          </template>
        </FormGroup>
      </FormSection>
    </form>

    <AggregateRowsDataSourceForm
      v-if="dataSource"
      ref="dataSourceForm"
      :dashboard="dashboard"
      :widget="widget"
      :data-source="dataSource"
      :default-values="dataSource"
      :store-prefix="storePrefix"
      @values-changed="onDataSourceValuesChanged"
    />
  </div>
</template>

<script>
import AggregateRowsDataSourceForm from '@jadawel/modules/dashboard/components/data_source/AggregateRowsDataSourceForm'
import dashboardWidgetSettings from '@jadawel/modules/arabase/dashboard/mixins/dashboardWidgetSettings'

export default {
  name: 'ProgressWidgetSettings',
  components: { AggregateRowsDataSourceForm },
  mixins: [dashboardWidgetSettings],
  data() {
    return {
      // Local copies because these are free-text numbers: pushing on every
      // keystroke would send a request per digit, and an in-progress value like
      // "1" on the way to "100" is not one the API should be asked to store.
      target: this.widget.target_value,
      warningThreshold: this.widget.warning_threshold,
      successThreshold: this.widget.success_threshold,
    }
  },
  computed: {
    displayStyle: {
      get() {
        return this.widget.display_style
      },
      set(value) {
        this.updateWidget({ display_style: value })
      },
    },
    targetInvalid() {
      const parsed = Number.parseFloat(this.target)
      return !Number.isFinite(parsed) || parsed <= 0
    },
    thresholdsInvalid() {
      return Number(this.warningThreshold) > Number(this.successThreshold)
    },
  },
  watch: {
    widget: {
      handler(widget) {
        // Another widget was selected, or the store rolled a failed update back.
        this.target = widget.target_value
        this.warningThreshold = widget.warning_threshold
        this.successThreshold = widget.success_threshold
      },
      deep: true,
    },
  },
  methods: {
    commitTarget() {
      if (this.targetInvalid) {
        return
      }
      const value = String(Number.parseFloat(this.target))
      if (value !== String(this.widget.target_value)) {
        this.updateWidget({ target_value: value })
      }
    },
    commitThresholds() {
      if (this.thresholdsInvalid) {
        return
      }
      const warning = Number(this.warningThreshold)
      const success = Number(this.successThreshold)
      const values = {}
      if (warning !== this.widget.warning_threshold) {
        values.warning_threshold = warning
      }
      if (success !== this.widget.success_threshold) {
        values.success_threshold = success
      }
      if (Object.keys(values).length > 0) {
        this.updateWidget(values)
      }
    },
  },
}
</script>
