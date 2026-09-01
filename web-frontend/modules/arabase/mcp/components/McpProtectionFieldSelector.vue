<template>
  <section
    class="mcp-protection-selector"
    aria-live="polite"
    :aria-busy="metadataLoading"
  >
    <p class="mcp-protection-selector__help">
      {{ $t('mcpProtection.fieldsHelp') }}
    </p>
    <p class="mcp-protection-selector__count">
      {{ $t('mcpProtection.selectedCount', { count: modelValue.length }) }}
    </p>
    <p
      v-if="metadataLoading"
      class="mcp-protection-selector__status"
      role="status"
      data-test-id="protected-fields-loading"
    >
      {{ $t('mcpProtection.fieldsLoading') }}
    </p>
    <p
      v-else-if="metadataError"
      class="mcp-protection-selector__status error"
      role="alert"
      data-test-id="protected-fields-error"
    >
      {{ $t('mcpProtection.fieldsLoadError') }}
    </p>
    <label class="mcp-protection-selector__search">
      <span class="sr-only">{{ $t('mcpProtection.searchFields') }}</span>
      <input
        v-model.trim="query"
        type="search"
        :disabled="disabled"
        :placeholder="$t('mcpProtection.searchPlaceholder')"
        data-test-id="protected-field-search"
      />
    </label>

    <div
        v-for="database in visibleDatabases"
      :key="database.id"
      class="mcp-protection-selector__database"
    >
      <div class="mcp-protection-selector__database-header">
        <h3 class="mcp-protection-selector__database-name">
          <bdi>{{ database.name }}</bdi>
        </h3>
        <button
          type="button"
          class="button button--small"
          :data-test-id="`select-database-${database.id}`"
          :disabled="disabled || metadataLoading"
          @click="beginDatabaseSelection(database)"
        >
          {{ $t('mcpProtection.selectDatabaseFields') }}
        </button>
      </div>
      <div
        v-if="databaseConfirmationId === database.id"
        class="mcp-protection-selector__scope-confirmation"
      >
        <label>
          <input
            v-model="confirmDatabaseScope"
            type="checkbox"
            :disabled="disabled || metadataLoading"
          />
          {{ $t('mcpProtection.confirmDatabaseScope', { name: database.name }) }}
        </label>
        <button
          type="button"
          class="button button--small button--primary"
          :disabled="disabled || !confirmDatabaseScope || metadataLoading"
          :data-test-id="`confirm-database-${database.id}`"
          @click="selectDatabaseFields(database)"
        >
          {{ $t('mcpProtection.confirmDatabaseSelection') }}
        </button>
      </div>
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
          :disabled="disabled || metadataLoading"
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
                :disabled="disabled || !fieldsByTable[table.id].length"
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
                :disabled="disabled"
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
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'status'],
  data() {
    return {
      fieldsByTable: {},
      loadingTableId: null,
      databaseLoadingId: null,
      errors: {},
      query: '',
      databaseConfirmationId: null,
      confirmDatabaseScope: false,
    }
  },
  computed: {
    metadataLoading() {
      return this.loadingTableId !== null || this.databaseLoadingId !== null
    },
    metadataError() {
      return Object.values(this.errors).some(Boolean)
    },
    visibleDatabases() {
      return this.databases.filter(
        (database) => this.visibleTables(database).length
      )
    },
  },
  mounted() {
    this.emitStatus()
  },
  methods: {
    emitStatus() {
      this.$emit('status', {
        loading: this.metadataLoading,
        error: this.metadataError,
      })
    },
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
      if (this.disabled) return
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
        this.emitStatus()
        return
      }
      await this.loadTable(table)
    },
    async loadTable(table) {
      this.loadingTableId = table.id
      this.errors = { ...this.errors, [table.id]: false }
      this.emitStatus()
      try {
        const { data } = await FieldService(this.$client).fetchAll(table.id)
        this.fieldsByTable = { ...this.fieldsByTable, [table.id]: data }
      } catch (error) {
        this.errors = { ...this.errors, [table.id]: true }
      } finally {
        this.loadingTableId = null
        this.emitStatus()
      }
    },
    beginDatabaseSelection(database) {
      if (this.disabled) return
      if (this.databaseConfirmationId === database.id) {
        this.databaseConfirmationId = null
        this.confirmDatabaseScope = false
      } else {
        this.databaseConfirmationId = database.id
        this.confirmDatabaseScope = false
      }
    },
    async selectDatabaseFields(database) {
      if (this.disabled || !this.confirmDatabaseScope) return
      this.databaseLoadingId = database.id
      this.errors = { ...this.errors }
      this.emitStatus()
      try {
        for (const table of database.tables) {
          if (!this.fieldsByTable[table.id]) {
            await this.loadTable(table)
          }
          if (this.errors[table.id]) {
            throw new Error('Unable to load database metadata')
          }
        }
        const selected = new Map(this.modelValue.map((field) => [field.id, field]))
        for (const table of database.tables) {
          for (const field of this.fieldsByTable[table.id] || []) {
            selected.set(field.id, {
              id: field.id,
              name: field.name,
              type: field.type,
              table: { id: table.id, name: table.name },
              database: { id: database.id, name: database.name },
            })
          }
        }
        this.$emit('update:modelValue', Array.from(selected.values()))
        this.databaseConfirmationId = null
        this.confirmDatabaseScope = false
      } catch (error) {
        // Keep the current selection intact and leave failed tables visibly
        // unresolved so a parent can block saving until retry succeeds.
      } finally {
        this.databaseLoadingId = null
        this.emitStatus()
      }
    },
    toggleField(database, table, field) {
      if (this.disabled) return
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
