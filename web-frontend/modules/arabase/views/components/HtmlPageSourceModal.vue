<template>
  <Modal ref="modal" :wide="true">
    <h2 class="box__title">{{ $t('htmlPageSourceModal.title') }}</h2>
    <p class="html-page-source__description">
      {{ $t('htmlPageSourceModal.description') }}
    </p>
    <!--
      dir="ltr" regardless of the interface language: this is source code, and
      an RTL paragraph direction reorders punctuation and tag brackets on screen
      into something that no longer reads as the code that will be saved.
    -->
    <textarea
      v-model="html"
      class="html-page-source__editor"
      dir="ltr"
      spellcheck="false"
      :readonly="readOnly"
      :placeholder="$t('htmlPageSourceModal.placeholder')"
    ></textarea>
    <div class="html-page-source__footer">
      <span class="html-page-source__size">
        {{ $t('htmlPageSourceModal.size', { bytes: html.length }) }}
      </span>
      <Button
        v-if="!readOnly"
        type="primary"
        :disabled="!changed"
        @click="save"
      >
        {{ $t('action.save') }}
      </Button>
    </div>
  </Modal>
</template>

<script>
import modal from '@jadawel/modules/core/mixins/modal'

/**
 * Read and hand-edit a page's HTML.
 *
 * A plain textarea rather than a code editor: the repository ships no editor
 * component, and pulling one in for what is a fallback path — pages are meant
 * to be written by an AI over MCP — would cost more than it returns.
 */
export default {
  name: 'HtmlPageSourceModal',
  mixins: [modal],
  props: {
    view: { type: Object, required: true },
    readOnly: { type: Boolean, required: false, default: false },
  },
  emits: ['save'],
  data() {
    return {
      html: '',
    }
  },
  computed: {
    changed() {
      return this.html !== this.view.html
    },
  },
  watch: {
    // Re-seed whenever the stored document changes, so a page edited from an
    // AI client while the modal is closed does not reopen showing stale source.
    'view.html': {
      immediate: true,
      handler(value) {
        this.html = value || ''
      },
    },
  },
  methods: {
    save() {
      this.$emit('save', this.html)
      this.hide()
    },
  },
}
</script>
