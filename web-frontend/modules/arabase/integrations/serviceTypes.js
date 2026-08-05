import {
  LocalBaserowListRowsServiceType,
  LocalBaserowTableServiceType,
} from '@jadawel/modules/integrations/localBaserow/serviceTypes'
import { DistributionViewAggregationType } from '@jadawel/modules/database/viewAggregationTypes'

/**
 * The frontend half of `arabase`'s grouped aggregation service.
 *
 * It deliberately extends `LocalBaserowTableServiceType` rather than the
 * `DataSourceServiceTypeMixin` version: the application builder lists every
 * service whose `isDataSource` is true in its data source picker, and this
 * service's only form is shaped for a dashboard widget. Making it selectable
 * there would show an empty form. Exposing it to the builder is a follow-up,
 * not an oversight.
 */
export class LocalBaserowGroupedAggregateRowsServiceType extends LocalBaserowTableServiceType {
  static getType() {
    return 'local_baserow_grouped_aggregate_rows'
  }

  get name() {
    return this.app.$i18n.t('arabaseServiceType.groupedAggregateRows')
  }

  get description() {
    return this.app.$i18n.t(
      'arabaseServiceType.groupedAggregateRowsDescription'
    )
  }

  get icon() {
    return 'iconoir-graph-up'
  }

  /**
   * Mirrors the backend's exclusion: a distribution needs a second grouping
   * level to mean anything once the rows are already bucketed.
   */
  get unsupportedAggregationTypes() {
    return [DistributionViewAggregationType.getType()]
  }

  getErrorMessage({ service }) {
    if (service !== undefined) {
      const series = service.aggregation_series || []
      if (series.length === 0) {
        return this.app.$i18n.t('arabaseServiceType.errorNoSeries')
      }
      if (series.some((s) => !s.field_id || !s.aggregation_type)) {
        return this.app.$i18n.t('arabaseServiceType.errorIncompleteSeries')
      }
      if (series.some((s) => s.trashed)) {
        return this.app.$i18n.t('arabaseServiceType.errorSeriesInError')
      }
      if ((service.aggregation_group_bys || []).some((g) => g.trashed)) {
        return this.app.$i18n.t('arabaseServiceType.errorGroupByInError')
      }
      if ((service.filters || []).some((filter) => filter.trashed)) {
        return this.app.$i18n.t('arabaseServiceType.errorFilterInError')
      }
    }
    return super.getErrorMessage({ service })
  }

  getOrder() {
    return 21
  }
}

/**
 * Rows narrowed to a date window, for the upcoming dates widget.
 *
 * Extends the list-rows type so the schema, record naming and formula path
 * handling all come for free — the window is the only difference, and it is
 * configured on the widget's own settings form rather than the builder's.
 */
export class LocalBaserowUpcomingRowsServiceType extends LocalBaserowListRowsServiceType {
  static getType() {
    return 'local_baserow_upcoming_rows'
  }

  get name() {
    return this.app.$i18n.t('arabaseServiceType.upcomingRows')
  }

  get description() {
    return this.app.$i18n.t('arabaseServiceType.upcomingRowsDescription')
  }

  get icon() {
    return 'iconoir-calendar'
  }

  /**
   * Kept out of the application builder's data source picker. It inherits the
   * list-rows form, which has no date-field control, so a builder user could
   * create one that can never dispatch. Giving it a builder form is a follow-up.
   */
  get isDataSource() {
    return false
  }

  getErrorMessage({ service }) {
    if (service !== undefined && service.table_id && !service.date_field_id) {
      return this.app.$i18n.t('arabaseServiceType.errorNoDateField')
    }
    return super.getErrorMessage({ service })
  }

  getOrder() {
    return 22
  }
}
