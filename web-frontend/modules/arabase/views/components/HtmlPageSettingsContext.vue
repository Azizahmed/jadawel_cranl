<template>
  <Context ref="context" class="html-page-settings">
    <div class="html-page-settings__section">
      <FormGroup
        small-label
        required
        :label="$t('htmlPageSettings.rowLimitLabel')"
        :helper-text="$t('htmlPageSettings.rowLimitHelp')"
      >
        <FormInput
          v-model="rowLimit"
          type="number"
          :min="1"
          :max="maxRowLimit"
          :disabled="readOnly"
          @blur="commitRowLimit"
        ></FormInput>
      </FormGroup>
    </div>
    <div class="html-page-settings__section">
      <SwitchInput
        :model-value="view.allow_external_resources"
        :disabled="readOnly"
        @update:model-value="confirmExternalResources"
      >
        {{ $t('htmlPageSettings.externalResourcesLabel') }}
      </SwitchInput>
      <!--
        Worth spelling out rather than hiding behind a tooltip: this is the one
        control on the page that widens what untrusted code can reach.
      -->
      <p class="html-page-settings__warning">
        {{ $t('htmlPageSettings.externalResourcesWarning') }}
      </p>
    </div>
  </Context>
</template>

<script>
import context from '@jadawel/modules/core/mixins/context'

// Mirrors MAX_ROW_LIMIT in backend/src/arabase/views/constants.py. The backend
// clamps rather than rejects, so a mismatch would be silently corrected there —
// this only keeps the input from offering a number that will not stick.
const MAX_ROW_LIMIT = 1000

export default {
  name: 'HtmlPageSettingsContext',
  mixins: [context],
  props: {
    view: { type: Object, required: true },
    readOnly: { type: Boolean, required: false, default: false },
  },
  emits: ['update'],
  data() {
    return {
      rowLimit: this.view.row_limit,
      maxRowLimit: MAX_ROW_LIMIT,
    }
  },
  watch: {
    'view.row_limit'(value) {
      this.rowLimit = value
    },
  },
  methods: {
    commitRowLimit() {
      const value = Math.max(
        1,
        Math.min(Number(this.rowLimit) || 1, MAX_ROW_LIMIT)
      )
      this.rowLimit = value
      if (value !== this.view.row_limit) {
        this.$emit('update', { row_limit: value })
      }
    },
    confirmExternalResources(value) {
      this.$emit('update', { allow_external_resources: value })
    },
  },
}
</script>
