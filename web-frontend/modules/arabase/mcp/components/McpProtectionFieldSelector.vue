<template>
  <section class="mcp-protection-selector" aria-live="polite">
    <p class="mcp-protection-selector__help">
      {{ $t('mcpProtection.fieldsHelp') }}
    </p>
    <p class="mcp-protection-selector__count">
      {{ $t('mcpProtection.selectedCount', { count: modelValue.length }) }}
    </p>
    <label class="mcp-protection-selector__search">
      <span class="sr-only">{{ $t('mcpProtection.searchFields') }}</span>
      <input
        v-model.trim="query"
        type="search"
        :placeholder="$t('mcpProtection.searchPlaceholder')"
        data-test-id="protected-field-search"
      />
    </label>

    <div
      v-for="database in visibleDatabases"
      :key="database.id"
      class="mcp-protection-selector__database"
    >
      <h3 class="mcp-protection-selector__database-name">
        <bdi>{{ database.name }}</bdi>
      </h3>
      <div
        v-for="table in visibleTables(database)"
        :key="table.id"
        class="mcp-protection-selector__table"
      >
        <button
          type="button"
          class="mcp-protection-selector__table-toggle"
          :data-test-id="`expand-table-${table.id}`"
          :aria-expanded="Boolean(fieldsByTable[table.id])"
          @click="toggleTable(database, table)"
        >
          <i
            :class="
              fieldsByTable[table.id]
                ? 'iconoir-nav-arrow-down'
                : 'iconoir-nav-arrow-left'
            "
          ></i>
          <bdi>{{ table.name }}</bdi>
        </button>
        <div v-if="loadingTableId === table.id" class="loading"></div>
        <p v-else-if="errors[table.id]" class="error">
          {{ $t('mcpProtection.fieldsLoadError') }}
        </p>
        <ul
          v-else-if="fieldsByTable[table.id]"
          class="mcp-protection-selector__fields"
        >
          <li class="mcp-protection-selector__select-all">
            <label>
              <input
                type="checkbox"
                :checked="tableSelectionState(table) === 'all'"
                :indeterminate="tableSelectionState(table) === 'some'"
                :disabled="!fieldsByTable[table.id].length"
                @change="toggleAllFields(table)"
              />
              {{ $t('mcpProtection.selectAllFields') }}
            </label>
          </li>
          <li v-for="field in fieldsByTable[table.id]" :key="field.id">
            <label class="mcp-protection-selector__field">
              <input
                type="checkbox"
                :data-test-id="`protected-field-${field.id}`"
                :checked="isSelected(field.id)"
                @change="toggleField(database, table, field)"
              />
              <bdi>{{ field.name }}</bdi>
              <span class="mcp-protection-selector__field-type">
                <bdi>{{ field.type }}</bdi>
              </span>
            </label>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script>
import FieldService from '@jadawel/modules/database/services/field'

export default {
  name: 'McpProtectionFieldSelector',
  props: {
    databases: { type: Array, required: true },
    modelValue: { type: Array, required: true },
  },
  emits: ['update:modelValue'],
  data() {
    return { fieldsByTable: {}, loadingTableId: null, errors: {}, query: '' }
  },
  computed: {
    visibleDatabases() {
      return this.databases.filter(
        (database) => this.visibleTables(database).length
      )
    },
  },
  methods: {
    visibleTables(database) {
      const normalizedQuery = this.query.trim()
      const query =
        normalizedQuery.length >= 2 ? normalizedQuery.toLocaleLowerCase() : ''
      return database.tables.filter((table) => {
        if (!query) return true
        if (
          `${database.name} ${table.name}`.toLocaleLowerCase().includes(query)
        ) {
          return true
        }
        return (this.fieldsByTable[table.id] || []).some((field) =>
          field.name.toLocaleLowerCase().includes(query)
        )
      })
    },
    tableSelectionState(table) {
      const fields = this.fieldsByTable[table.id] || []
      if (!fields.length) return 'none'
      const selected = fields.filter((field) =>
        this.isSelected(field.id)
      ).length
      return selected === 0
        ? 'none'
        : selected === fields.length
          ? 'all'
          : 'some'
    },
    toggleAllFields(table) {
      const fields = this.fieldsByTable[table.id] || []
      const selected = new Set(this.modelValue.map((field) => field.id))
      if (this.tableSelectionState(table) === 'all') {
        fields.forEach((field) => selected.delete(field.id))
      } else {
        fields.forEach((field) => selected.add(field.id))
      }
      this.$emit(
        'update:modelValue',
        fields
          .filter((field) => selected.has(field.id))
          .reduce(
            (result, field) => {
              const existing = this.modelValue.find(
                (item) => item.id === field.id
              )
              return [
                ...result,
                existing || {
                  id: field.id,
                  name: field.name,
                  type: field.type,
                  table: { id: table.id, name: table.name },
                },
              ]
            },
            this.modelValue.filter(
              (field) => !fields.some((item) => item.id === field.id)
            )
          )
      )
    },
    isSelected(fieldId) {
      return this.modelValue.some((field) => field.id === fieldId)
    },
    async toggleTable(database, table) {
      if (this.fieldsByTable[table.id]) {
        const next = { ...this.fieldsByTable }
        delete next[table.id]
        this.fieldsByTable = next
        return
      }
      this.loadingTableId = table.id
      this.errors = { ...this.errors, [table.id]: false }
      try {
        const { data } = await FieldService(this.$client).fetchAll(table.id)
        this.fieldsByTable = { ...this.fieldsByTable, [table.id]: data }
      } catch (error) {
        this.errors = { ...this.errors, [table.id]: true }
      } finally {
        this.loadingTableId = null
      }
    },
    toggleField(database, table, field) {
      if (this.isSelected(field.id)) {
        this.$emit(
          'update:modelValue',
          this.modelValue.filter((selected) => selected.id !== field.id)
        )
        return
      }
      this.$emit('update:modelValue', [
        ...this.modelValue,
        {
          id: field.id,
          name: field.name,
          type: field.type,
          table: { id: table.id, name: table.name },
          database: { id: database.id, name: database.name },
        },
      ])
    },
  },
}
</script>
