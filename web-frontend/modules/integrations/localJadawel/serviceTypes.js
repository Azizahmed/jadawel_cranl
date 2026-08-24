import {
  ServiceType,
  DataSourceServiceTypeMixin,
  WorkflowActionServiceTypeMixin,
  TriggerServiceTypeMixin,
} from '@jadawel/modules/core/serviceTypes'
import { LocalJadawelIntegrationType } from '@jadawel/modules/integrations/localJadawel/integrationTypes'
import LocalJadawelUpsertRowServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelUpsertRowServiceForm'
import LocalJadawelUpdateRowServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelUpdateRowServiceForm'
import LocalJadawelDeleteRowServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelDeleteRowServiceForm'
import { uuid } from '@jadawel/modules/core/utils/string'
import LocalJadawelAdhocHeader from '@jadawel/modules/integrations/localJadawel/components/integrations/LocalJadawelAdhocHeader'
import { DistributionViewAggregationType } from '@jadawel/modules/database/viewAggregationTypes'
import LocalJadawelSignalTriggerServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelSignalTriggerServiceForm'
import LocalJadawelGetRowForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelGetRowForm'
import LocalJadawelListRowsForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelListRowsForm'
import LocalJadawelAggregateRowsForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelAggregateRowsForm'

export class LocalJadawelTableServiceType extends ServiceType {
  get integrationType() {
    return this.app.$registry.get(
      'integration',
      LocalJadawelIntegrationType.getType()
    )
  }

  getDataSchema(service) {
    return service.schema
  }

  getContextDataSchema(service) {
    return service.context_data_schema
  }

  /**
   * Given an array of tables, returns the supported tables for this service type.
   * By default, we return all tables, but specific service types can override this
   * method to restrict the tables that can be selected.
   * @param {Array} tables - The array of tables to filter.
   * @returns {Array} - The supported tables.
   */
  supportedTables(tables) {
    return tables
  }

  /**
   * Responsible for determining if this service is in error. It will be if the
   * `table_id` is missing.
   * @param service - The service object.
   * @returns {boolean} - If the service is valid.
   */
  getErrorMessage({ service }) {
    if (service !== undefined) {
      if (!service.table_id) {
        return this.app.$i18n.t('serviceType.errorNoTableSelected')
      }
    }
    return super.getErrorMessage({ service })
  }

  /**
   * Responsible for returning the description of the service. This is used in
   * the UI to display a human-readable description of the service.
   *
   * @param service - The service object.
   * @param application - The application object.
   * @returns {string} - The description of the service.
   */
  getDescription(service, application) {
    const integration = this.app.$store.getters[
      'integration/getIntegrationById'
    ](application, service.integration_id)

    const databases = integration?.context_data?.databases || []

    const tableSelected = databases
      .map((database) => database.tables)
      .flat()
      .find(({ id }) => id === service.table_id)

    let description = this.name
    if (service.table_id && tableSelected) {
      description += ` - ${tableSelected.name}`
    }

    if (this.isInError({ service })) {
      description += ` - ${this.getErrorMessage({ service })}`
    }

    return description
  }

  prepareValuePath(service, path) {
    if (path.length < 1) {
      return path
    }

    const schema = this.getDataSchema(service)

    const [field, ...rest] = path
    let humanName = field

    if (schema && typeof field === 'string' && field.startsWith('field_')) {
      if (this.returnsList) {
        if (schema.items?.properties?.[field]?.title) {
          humanName = schema.items.properties[field].title
        }
      } else if (schema.properties[field]?.title) {
        humanName = schema.properties[field].title
      }
    }

    return [humanName, ...rest]
  }
}

export class DataSourceLocalJadawelTableServiceType extends DataSourceServiceTypeMixin(
  LocalJadawelTableServiceType
) {
  getIdProperty(service, record) {
    return 'id'
  }

  /**
   * Responsible for determining if this service is in error. It will be if the
   * `table_id` is missing, or if one or more filters/sortings point to a field that
   * has been trashed.
   * @param service - The service object.
   * @returns {boolean} - If the service is valid.
   */
  getErrorMessage({ service }) {
    if (service !== undefined) {
      const filtersInError = service.filters?.some((filter) => filter.trashed)
      if (filtersInError) {
        return this.app.$i18n.t('serviceType.errorFilterInError')
      }

      const sortingsInError = service.sortings?.some(
        (sorting) => sorting.trashed
      )
      if (sortingsInError) {
        return this.app.$i18n.t('serviceType.errorSortingInError')
      }
    }
    return super.getErrorMessage({ service })
  }
}

export class LocalJadawelGetRowServiceType extends DataSourceLocalJadawelTableServiceType {
  static getType() {
    return 'local_jadawel_get_row'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelGetRow')
  }

  get formComponent() {
    return LocalJadawelGetRowForm
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelGetRowDescription')
  }

  get icon() {
    return 'iconoir-pin'
  }

  /**
   * A hook called prior to an update to modify the filters and
   * sortings if the `table_id` changes from one ID to another.
   * The same behavior happens in the backend, this reset is to
   * make the filter/sort components reset properly.
   */
  beforeUpdate(newValues, oldValues) {
    if (
      oldValues.table_id !== null &&
      newValues.table_id !== oldValues.table_id
    ) {
      newValues.filters = []
      newValues.sortings = []
    }
    return newValues
  }

  getOrder() {
    return 10
  }
}

export class LocalJadawelListRowsServiceType extends DataSourceLocalJadawelTableServiceType {
  static getType() {
    return 'local_jadawel_list_rows'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelListRows')
  }

  get formComponent() {
    return LocalJadawelListRowsForm
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelListRowsDescription')
  }

  get icon() {
    return 'iconoir-list'
  }

  /**
   * The Local Jadawel adhoc filtering, sorting and searching component.
   */
  get adhocHeaderComponent() {
    return LocalJadawelAdhocHeader
  }

  get returnsList() {
    return true
  }

  getMaxResultLimit(service) {
    return this.app.$config.public.integrationLocalJadawelPageSizeLimit
  }

  /**
   * A hook called prior to an update to modify the filters and
   * sortings if the `table_id` changes from one ID to another.
   * The same behavior happens in the backend, this reset is to
   * make the filter/sort components reset properly.
   */
  beforeUpdate(newValues, oldValues) {
    if (
      oldValues.table_id !== null &&
      newValues.table_id !== oldValues.table_id
    ) {
      newValues.filters = []
      newValues.sortings = []
    }
    return newValues
  }

  getDefaultCollectionFields(service) {
    return Object.keys(service.schema.items.properties)
      .filter(
        (field) =>
          field !== 'id' &&
          service.schema.items.properties[field].original_type !== 'formula' // every formula has different properties
      )
      .map((field) => {
        const type = service.schema.items.properties[field].type
        const originalType =
          service.schema.items.properties[field].original_type
        let outputType = 'text'
        let valueFormula = `get('current_record.${field}')`
        if (originalType === 'boolean') {
          outputType = 'boolean'
        } else if (originalType === 'rating') {
          outputType = 'rating'
        } else if (originalType === 'url') {
          return {
            link_name: { formula: valueFormula },
            name: service.schema.items.properties[field].title,
            id: uuid(), // Temporary id
            navigate_to_page_id: null,
            navigate_to_url: { formula: valueFormula },
            navigation_type: 'custom',
            page_parameters: [],
            target: 'blank',
            type: 'link',
          }
        } else if (originalType === 'file') {
          return {
            id: uuid(),
            name: service.schema.items.properties[field].title,
            type: 'image',
            src: { formula: `get('current_record.${field}.*.url')` },
            alt: { formula: `get('current_record.${field}.*.visible_name')` },
          }
        } else if (
          originalType === 'last_modified_by' ||
          originalType === 'created_by'
        ) {
          valueFormula = `get('current_record.${field}.name')`
        } else if (originalType === 'single_select') {
          valueFormula = `get('current_record.${field}.value')`
        }
        if (originalType === 'multiple_collaborators') {
          valueFormula = `get('current_record.${field}.*.name')`
        } else if (type === 'array') {
          valueFormula = `get('current_record.${field}.*.value')`
        }
        return {
          name: service.schema.items.properties[field].title,
          type: outputType,
          value: { formula: valueFormula },
          id: uuid(), // Temporary id
        }
      })
  }

  getRecordName(service, record) {
    const schema = this.getDataSchema(service)
    if (!schema?.items?.properties) {
      return ''
    }

    // Search the primary field using the metadata in the schema
    const primaryField = Object.values(schema.items.properties).find(
      ({ metadata }) => metadata?.primary
    )

    return record[primaryField.title]
  }

  getOrder() {
    return 20
  }
}

export class LocalJadawelAggregateRowsServiceType extends DataSourceLocalJadawelTableServiceType {
  static getType() {
    return 'local_jadawel_aggregate_rows'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelAggregateRows')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelAggregateRowsDescription')
  }

  get formComponent() {
    return LocalJadawelAggregateRowsForm
  }

  get icon() {
    return 'iconoir-sigma-function'
  }

  /**
   * Local Jadawel aggregate rows does not currently support the distribution
   * aggregation type, this will be resolved in a future release.
   */
  get unsupportedAggregationTypes() {
    return [DistributionViewAggregationType.getType()]
  }

  getResult(service, data) {
    if (data && data.result !== undefined && service !== undefined) {
      const field = service.context_data?.field
      if (!field || !service.aggregation_type) {
        // Public dashboards intentionally omit private formatting context.
        return data.result
      }
      const fieldType = this.app.$registry.get('field', field.type)
      const aggregationType = this.app.$registry.get(
        'viewAggregation',
        service.aggregation_type
      )
      const formattedResult = aggregationType.formatValue(data.result, {
        field,
        fieldType,
      })
      return formattedResult
    }
    return null
  }

  getErrorMessage({ service }) {
    if (service !== undefined) {
      if (!service.field_id) {
        return this.app.$i18n.t('serviceType.errorNoFieldSelected')
      }
      if (!service.aggregation_type) {
        return this.app.$i18n.t('serviceType.errorNoAggregationTypeSelected')
      }
      const filtersInError = service.filters.some((filter) => filter.trashed)
      if (filtersInError) {
        return this.app.$i18n.t('serviceType.errorFilterInError')
      }
    }
    return super.getErrorMessage({ service })
  }

  getDescription(service, application) {
    const integration = this.app.$store.getters[
      'integration/getIntegrationById'
    ](application, service.integration_id)

    const databases = integration?.context_data?.databases || []

    const tableSelected = databases
      .map((database) => database.tables)
      .flat()
      .find(({ id }) => id === service.table_id)

    if (service.table_id && tableSelected) {
      const defaultTableDescription = `${this.name} - ${tableSelected.name}`
      if (service.field_id) {
        if (service.context_data.field) {
          const fieldName = service.context_data.field.name
          return `${defaultTableDescription} - ${fieldName}`
        } else {
          return `${defaultTableDescription} - ${this.app.$i18n.t(
            'serviceType.trashedField'
          )}`
        }
      }

      return defaultTableDescription
    }

    return this.name
  }

  getOrder() {
    return 30
  }
}

export class LocalJadawelCreateRowWorkflowServiceType extends WorkflowActionServiceTypeMixin(
  LocalJadawelTableServiceType
) {
  static getType() {
    return 'local_jadawel_create_row'
  }

  /**
   * The Local Jadawel create row service will only work on tables which are
   * not data-synced, or are data-synced but are two-way synced.
   * @param {Array} tables - The array of tables to filter.
   * @returns {Array} - The supported tables.
   */
  supportedTables(tables) {
    return tables.filter(
      (table) => !table.is_data_sync || table.is_two_way_data_sync
    )
  }

  get icon() {
    return 'iconoir-plus'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelCreateRow')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelCreateRowDescription')
  }

  get formComponent() {
    return LocalJadawelUpsertRowServiceForm
  }
}

export class LocalJadawelUpdateRowWorkflowServiceType extends WorkflowActionServiceTypeMixin(
  LocalJadawelTableServiceType
) {
  static getType() {
    return 'local_jadawel_update_row'
  }

  get icon() {
    return 'iconoir-edit-pencil'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelUpdateRow')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelUpdateRowDescription')
  }

  get formComponent() {
    return LocalJadawelUpdateRowServiceForm
  }
}

export class LocalJadawelDeleteRowWorkflowServiceType extends WorkflowActionServiceTypeMixin(
  LocalJadawelTableServiceType
) {
  static getType() {
    return 'local_jadawel_delete_row'
  }

  get icon() {
    return 'iconoir-bin'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelDeleteRow')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelDeleteRowDescription')
  }

  get formComponent() {
    return LocalJadawelDeleteRowServiceForm
  }

  /**
   * The Local Jadawel delete row service will only work on tables which are
   * not data-synced, or are data-synced but are two-way synced.
   * @param {Array} tables - The array of tables to filter.
   * @returns {Array} - The supported tables.
   */
  supportedTables(tables) {
    return tables.filter(
      (table) => !table.is_data_sync || table.is_two_way_data_sync
    )
  }
}

export class LocalJadawelTriggerServiceType extends TriggerServiceTypeMixin(
  LocalJadawelTableServiceType
) {
  get returnsList() {
    return true
  }

  getErrorMessage({ service }) {
    if (service !== undefined) {
      if (!service.table_id) {
        this.app.$i18n.t('serviceType.errorNoTableSelected')
      }
    }
    return super.getErrorMessage({ service })
  }
}

export class LocalJadawelRowsCreatedTriggerServiceType extends LocalJadawelTriggerServiceType {
  static getType() {
    return 'rows_created'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelRowsCreated')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelRowsCreatedDescription')
  }

  get icon() {
    return 'iconoir-plus'
  }

  get formComponent() {
    return LocalJadawelSignalTriggerServiceForm
  }
}

export class LocalJadawelRowsUpdatedTriggerServiceType extends LocalJadawelTriggerServiceType {
  static getType() {
    return 'rows_updated'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelRowsUpdated')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelRowsUpdatedDescription')
  }

  get icon() {
    return 'iconoir-edit'
  }

  get formComponent() {
    return LocalJadawelSignalTriggerServiceForm
  }
}

export class LocalJadawelRowsDeletedTriggerServiceType extends LocalJadawelTriggerServiceType {
  static getType() {
    return 'rows_deleted'
  }

  get name() {
    return this.app.$i18n.t('serviceType.localJadawelRowsDeleted')
  }

  get description() {
    return this.app.$i18n.t('serviceType.localJadawelRowsDeletedDescription')
  }

  get icon() {
    return 'iconoir-trash'
  }

  get formComponent() {
    return LocalJadawelSignalTriggerServiceForm
  }
}
