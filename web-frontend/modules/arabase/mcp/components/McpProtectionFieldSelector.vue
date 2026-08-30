<template>
  <section class="mcp-protection-selector" aria-live="polite">
    <p class="mcp-protection-selector__help">
      {{ $t('mcpProtection.fieldsHelp') }}
    </p>
    <p class="mcp-protection-selector__count">
      {{ $t('mcpProtection.selectedCount', { count: modelValue.length }) }}
    </p>

    <div
      v-for="database in databases"
      :key="database.id"
      class="mcp-protection-selector__database"
    >
      <h3 class="mcp-protection-selector__database-name">
        <bdi>{{ database.name }}</bdi>
      </h3>
      <div
        v-for="table in database.tables"
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
    return { fieldsByTable: {}, loadingTableId: null, errors: {} }
  },
  methods: {
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
