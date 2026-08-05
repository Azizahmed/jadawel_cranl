<template>
  <div class="control__elements">
    <a
      v-if="isValidLinkURL"
      :href="copy && copy.url"
      target="_blank"
      rel="nofollow noopener noreferrer"
    >
      {{ labelOrURL }}
    </a>
    <span v-else>
      {{ labelOrURL }}
    </span>
  </div>
</template>

<script>
import rowEditField from '@jadawel/modules/database/mixins/rowEditField'
import rowEditFieldInput from '@jadawel/modules/database/mixins/rowEditFieldInput'
import linkURLField from '@jadawel/modules/database/mixins/linkURLField'

export default {
  mixins: [rowEditField, rowEditFieldInput, linkURLField],
  computed: {
    isValidLinkURL() {
      return this.copy && this.isValid(this.copy)
    },
    labelOrURL() {
      return this.getLabelOrURL(this.copy)
    },
  },
}
</script>
