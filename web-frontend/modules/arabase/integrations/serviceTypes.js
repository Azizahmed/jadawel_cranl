import { LocalBaserowTableServiceType } from '@baserow/modules/integrations/localBaserow/serviceTypes'
import { DistributionViewAggregationType } from '@baserow/modules/database/viewAggregationTypes'

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
