<template>
  <form :class="{ 'service-form--small': small }" @submit.prevent>
    <div>
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
      <div v-if="values.integration_id && values.table_id" class="row">
        <div class="col col-6">
          <FormGroup
            small-label
            :label="$t('localJadawelGetRowForm.rowFieldLabel')"
            required
          >
            <InjectedFormulaInput
              v-model="values.row_id"
              :placeholder="$t('localJadawelGetRowForm.rowFieldPlaceHolder')"
            />
            <template #helper>
              {{ $t('localJadawelGetRowForm.rowFieldHelpText') }}
            </template>
          </FormGroup>
        </div>
      </div>
      <ServiceRefinementForms
        v-if="!fieldsLoading && values.table_id"
        class="margin-top-2"
        :small="small"
        :values="values"
        :table-fields="tableFields"
        show-filter
        show-search
      />
      <div v-if="fieldsLoading" class="loading-spinner"></div>
    </div>
  </form>
</template>

<script>
import form from '@jadawel/modules/core/mixins/form'
import InjectedFormulaInput from '@jadawel/modules/core/components/formula/InjectedFormulaInput'
import localJadawelService from '@jadawel/modules/integrations/localJadawel/mixins/localJadawelService'
import LocalJadawelServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelServiceForm'
import ServiceRefinementForms from '@jadawel/modules/integrations/localJadawel/components/services/ServiceRefinementForms'

export default {
  components: {
    LocalJadawelServiceForm,
    InjectedFormulaInput,
    ServiceRefinementForms,
  },
  mixins: [form, localJadawelService],
  data() {
    return {
      allowedValues: [
        'table_id',
        'view_id',
        'row_id',
        'search_query',
        'filters',
        'filter_type',
      ],
      values: {
        table_id: null,
        view_id: null,
        row_id: {},
        search_query: {},
        filters: [],
        filter_type: 'AND',
      },
    }
  },
}
</script>
