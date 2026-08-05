<template>
  <form :class="{ 'service-form--small': small }" @submit.prevent>
    <div>
      <div class="row">
        <div class="col col-12">
          <LocalBaserowServiceForm
            :application="application"
            :service-type="serviceType"
            :default-values="defaultValues"
            :enable-integration-picker="enableIntegrationPicker"
            @values-changed="values = { ...values, ...$event }"
          ></LocalBaserowServiceForm>
        </div>
      </div>
      <div v-if="values.integration_id && values.table_id" class="row">
        <div class="col col-6">
          <FormGroup
            small-label
            :label="$t('localBaserowGetRowForm.rowFieldLabel')"
            required
          >
            <InjectedFormulaInput
              v-model="values.row_id"
              :placeholder="$t('localBaserowGetRowForm.rowFieldPlaceHolder')"
            />
            <template #helper>
              {{ $t('localBaserowGetRowForm.rowFieldHelpText') }}
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
import localBaserowService from '@jadawel/modules/integrations/localBaserow/mixins/localBaserowService'
import LocalBaserowServiceForm from '@jadawel/modules/integrations/localBaserow/components/services/LocalBaserowServiceForm'
import ServiceRefinementForms from '@jadawel/modules/integrations/localBaserow/components/services/ServiceRefinementForms'

export default {
  components: {
    LocalBaserowServiceForm,
    InjectedFormulaInput,
    ServiceRefinementForms,
  },
  mixins: [form, localBaserowService],
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
