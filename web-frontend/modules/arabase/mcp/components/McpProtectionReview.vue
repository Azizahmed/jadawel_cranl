<template>
  <section class="mcp-protection-review">
    <h3>{{ $t('mcpProtection.reviewTitle') }}</h3>
    <dl class="mcp-protection-review__details">
      <div>
        <dt>{{ $t('mcpEndpointForm.nameLabel') }}</dt>
        <dd>
          <bdi>{{ name }}</bdi>
        </dd>
      </div>
      <div>
        <dt>{{ $t('mcpEndpointForm.workspaceLabel') }}</dt>
        <dd>
          <bdi>{{ workspaceName }}</bdi>
        </dd>
      </div>
    </dl>
    <ul v-if="fields.length" class="mcp-protection-review__fields">
      <li v-for="field in fields" :key="field.id">
        <strong
          ><bdi>{{ field.name }}</bdi></strong
        >
        <span
          ><bdi>{{ field.database.name }} / {{ field.table.name }}</bdi></span
        >
      </li>
    </ul>
    <label v-else class="mcp-protection-review__empty-confirmation">
      <input
        type="checkbox"
        :checked="confirmEmptyPolicy"
        data-test-id="confirm-empty-policy"
        @change="$emit('update:confirmEmptyPolicy', $event.target.checked)"
      />
      {{ $t('mcpProtection.confirmEmptyPolicy') }}
    </label>
  </section>
</template>

<script>
export default {
  name: 'McpProtectionReview',
  props: {
    name: { type: String, required: true },
    workspaceName: { type: String, required: true },
    fields: { type: Array, required: true },
    confirmEmptyPolicy: { type: Boolean, required: true },
  },
  emits: ['update:confirmEmptyPolicy'],
}
</script>
