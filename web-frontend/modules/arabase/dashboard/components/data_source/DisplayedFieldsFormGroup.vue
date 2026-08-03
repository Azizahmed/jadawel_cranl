<template>
  <FormGroup
    :label="$t('displayedFields.label')"
    :helper-text="$t('displayedFields.help')"
    class="margin-bottom-2"
    small-label
    horizontal
    horizontal-narrow
  >
    <Dropdown
      :model-value="modelValue"
      :multiple="true"
      :show-search="true"
      fixed-items
      :disabled="fields.length === 0"
      @update:model-value="onChange"
    >
      <DropdownItem
        v-for="field in fields"
        :key="field.id"
        :name="field.name"
        :value="field.id"
        :icon="fieldIconClass(field)"
      >
      </DropdownItem>
    </Dropdown>
  </FormGroup>
</template>

<script>
export default {
  name: 'DisplayedFieldsFormGroup',
  props: {
    modelValue: {
      type: Array,
      required: false,
      default: () => [],
    },
    fields: {
      type: Array,
      required: true,
    },
    maxFields: {
      type: Number,
      required: false,
      default: 6,
    },
  },
  emits: ['update:modelValue'],
  methods: {
    fieldIconClass(field) {
      return this.$registry.get('field', field.type).iconClass
    },
    onChange(value) {
      const selection = Array.isArray(value) ? value : []
      // The API enforces the same ceiling. Trimming here rather than rejecting
      // keeps the dropdown usable: the click that went over the limit is simply
      // not applied instead of producing an error toast.
      this.$emit('update:modelValue', selection.slice(0, this.maxFields))
    },
  },
}
</script>
