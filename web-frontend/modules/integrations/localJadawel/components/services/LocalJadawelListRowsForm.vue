<template>
  <form :class="{ 'service-form--small': small }" @submit.prevent>
    <div class="row">
      <div class="col col-12">
        <LocalJadawelServiceForm
          :application="application"
          :service-type="serviceType"
          :default-values="defaultValues"
          :enable-integration-picker="enableIntegrationPicker"
          @values-changed="values = { ...values, ...$event }"
        ></LocalJadawelServiceForm>
      </div>
    </div>

    <ServiceRefinementForms
      v-if="!fieldsLoading && values.table_id"
      :small="small"
      :values="values"
      :table-fields="tableFields"
      show-filter
      show-sort
      show-search
    >
      <template #additional-buttons>
        <FormGroup
          class="margin-top-1"
          small-label
          :label="$t('localJadawelListRowsForm.defaultResultCount')"
          :helper-text="$t('localJadawelListRowsForm.defaultResultCountHelp')"
          required
          :error-message="getFirstErrorMessage('default_result_count')"
        >
          <FormInput
            v-model="v$.values.default_result_count.$model"
            class="service-form__result-count-input"
            :placeholder="
              $t('localJadawelListRowsForm.defaultResultCountPlaceholder')
            "
            :to-value="(value) => parseFloat(value)"
            type="number"
          />
        </FormGroup>
      </template>
      <template #additional-tabs>
        <Tab
          :title="$t('localJadawelListRowsForm.advancedConfig')"
          class="service-form__search-form-tab"
        >
          <FormGroup
            class="margin-bottom-2"
            small-label
            :label="$t('localJadawelListRowsForm.defaultResultCount')"
            :helper-text="$t('localJadawelListRowsForm.defaultResultCountHelp')"
            required
            :error-message="getFirstErrorMessage('default_result_count')"
          >
            <FormInput
              v-model="v$.values.default_result_count.$model"
              class="service-form__result-count-input"
              :placeholder="
                $t('localJadawelListRowsForm.defaultResultCountPlaceholder')
              "
              :to-value="(value) => parseFloat(value)"
              type="number"
            />
          </FormGroup>
        </Tab>
      </template>
    </ServiceRefinementForms>
    <div v-if="fieldsLoading" class="loading-spinner"></div>
  </form>
</template>

<script>
import form from '@jadawel/modules/core/mixins/form'
import localJadawelService from '@jadawel/modules/integrations/localJadawel/mixins/localJadawelService'
import ServiceRefinementForms from '@jadawel/modules/integrations/localJadawel/components/services/ServiceRefinementForms'
import Tab from '@jadawel/modules/core/components/Tab'
import {
  required,
  minValue,
  maxValue,
  helpers,
  integer,
} from '@vuelidate/validators'
import { useVuelidate } from '@vuelidate/core'
import LocalJadawelServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelServiceForm'

export default {
  components: {
    LocalJadawelServiceForm,
    ServiceRefinementForms,
    Tab,
  },
  mixins: [form, localJadawelService],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: [
        'table_id',
        'view_id',
        'search_query',
        'filters',
        'filter_type',
        'sortings',
        'default_result_count',
      ],
      values: {
        table_id: null,
        view_id: null,
        search_query: {},
        filters: [],
        sortings: [],
        filter_type: 'AND',
        default_result_count: null,
      },
    }
  },
  computed: {
    maxResultLimit() {
      return this.service
        ? this.$registry
            .get('service', this.service.type)
            .getMaxResultLimit(this.service)
        : null
    },
  },

  validations() {
    return {
      values: {
        default_result_count: {
          required: helpers.withMessage(
            this.$t('error.requiredField'),
            required
          ),
          integer: helpers.withMessage(this.$t('error.integerField'), integer),
          minValue: helpers.withMessage(
            this.$t('error.minValueField', { min: 0 }),
            minValue(0)
          ),
          maxValue: helpers.withMessage(
            this.$t('error.maxValueField', { max: this.maxResultLimit }),
            maxValue(this.maxResultLimit)
          ),
        },
      },
    }
  },
}
</script>
