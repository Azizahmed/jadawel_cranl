<template>
  <div class="dashboard__application">
    <div class="dashboard__application-wrapper" @click="$emit('click')">
      <div class="dashboard__application-icon">
        <i :class="application._.type.iconClass"></i>
      </div>

      <div class="dashboard__application-details">
        <div class="dashboard__application-name">
          <div class="dashboard__application-name-text">
            <Editable
              ref="rename"
              :value="application.name"
              @change="renameApplication(application, $event)"
            ></Editable>
          </div>
        </div>

        <div class="dashboard__application-more">
          {{ getApplicationTypeName(application) }}
          <template v-for="part in statParts" :key="part">
            <span class="dashboard__application-more-separator">&#8226;</span>
            {{ part }}
          </template>
          <ClientOnly>
            <span class="dashboard__application-more-separator">&#8226;</span>
            {{ $t('dashboardApplication.createdAt') }} {{ humanCreatedAt }}
          </ClientOnly>
        </div>
      </div>
    </div>

    <span ref="contextLink" class="dashboard__application-more-button">
      <ButtonIcon
        icon="jadawel-icon-more-vertical"
        @click="$refs.context.toggle($refs.contextLink, 'bottom', 'right', 0)"
      ></ButtonIcon>
    </span>

    <component
      :is="getApplicationContextComponent(application)"
      ref="context"
      :application="application"
      :workspace="workspace"
      @rename="handleRenameApplication()"
    ></component>
  </div>
</template>

<script>
import application from '@jadawel/modules/core/mixins/application'
import { getHumanPeriodAgoCount } from '@jadawel/modules/core/utils/date'
import { pluralKeys } from '@jadawel/modules/core/utils/plural'

export default {
  mixins: [application],
  props: {
    application: {
      type: Object,
      required: true,
    },
    workspace: {
      type: Object,
      required: true,
    },
    /**
     * Counters for this application, or null. Null covers three different cases
     * that all render the same way — still loading, not a database, or the
     * request failed — because none of them should show a number.
     */
    stats: {
      type: Object,
      required: false,
      default: null,
    },
  },
  emits: ['click'],
  computed: {
    humanCreatedAt() {
      const { period, count } = getHumanPeriodAgoCount(
        this.application.created_on
      )
      return this.$t(`datetime.${period}Ago`, { count })
    },
    /**
     * The "10 tables · 94 columns · 66 rows" segments of the subtitle.
     *
     * Row count is dropped when the backend reports `rows_exact: false` — that
     * means the workspace had too many tables to count in one pass, and showing
     * a partial total would be worse than showing none.
     */
    statParts() {
      if (!this.stats) {
        return []
      }

      const parts = [
        this.counted('dashboardApplication.tableCount', this.stats.table_count),
        this.counted('dashboardApplication.fieldCount', this.stats.field_count),
      ]

      if (this.stats.rows_exact && this.stats.row_count !== null) {
        parts.push(
          this.counted('dashboardApplication.rowCount', this.stats.row_count)
        )
      }

      return parts
    },
  },
  methods: {
    /**
     * Resolve a count message through CLDR rather than vue-i18n's plurals.
     *
     * vue-i18n applies the English rule to every locale here, which collapses
     * Arabic's six categories into "one" and "everything else" and produces
     * `24 أعمدة` where the language wants `24 عمودًا`. See `utils/plural`.
     */
    counted(base, count) {
      const keys = pluralKeys(base, this.$i18n.locale, count)
      const key =
        keys.find((candidate) => this.$te(candidate)) || keys[keys.length - 1]
      return this.$t(key, { count })
    },
  },
}
</script>
