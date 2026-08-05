<template>
  <div class="control__elements">
    <Button
      v-if="isValidLinkURL"
      tag="a"
      size="tiny"
      type="secondary"
      :href="copy && copy.url"
      target="_blank"
      rel="nofollow noopener noreferrer"
    >
      {{ labelOrURL }}
    </Button>
    <Button v-else tag="a" size="tiny" type="secondary" disabled>
      {{ labelOrURL }}
    </Button>
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
