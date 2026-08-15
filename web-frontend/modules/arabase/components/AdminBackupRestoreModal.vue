<template>
  <Modal ref="modal">
    <h2 class="box__title">{{ $t('adminBackupRestore.title') }}</h2>

    <p>{{ $t('adminBackupRestore.description') }}</p>

    <!-- Stated plainly rather than buried in help text. The reason this restore
         is safe is that it will not touch the live database, and an operator
         reaching for it in a panic should be able to see that in one line. -->
    <Alert type="info">
      {{ $t('adminBackupRestore.notDestructive') }}
    </Alert>

    <div v-if="run" class="admin-backup__restore-key">
      <code>{{ run.key }}</code>
    </div>

    <form @submit.prevent="restore">
      <FormGroup
        :label="$t('adminBackupRestore.targetLabel')"
        :helper-text="$t('adminBackupRestore.targetHelp')"
        :error="error !== ''"
        required
        small-label
      >
        <FormInput
          v-model="target"
          :error="error !== ''"
          placeholder="postgresql://user:password@host:5432/jadawel_restore"
          size="large"
        />
        <template #error>{{ error }}</template>
      </FormGroup>

      <div class="actions actions--right">
        <Button type="secondary" @click.prevent="hide">
          {{ $t('action.cancel') }}
        </Button>
        <Button
          type="primary"
          :disabled="target === '' || loading"
          :loading="loading"
        >
          {{ $t('adminBackupRestore.confirm') }}
        </Button>
      </div>
    </form>

    <Alert v-if="queued" type="success">
      {{ $t('adminBackupRestore.queued', { target: queued }) }}
    </Alert>
  </Modal>
</template>

<script>
import BackupService from '@jadawel/modules/arabase/services/backup'
import modal from '@jadawel/modules/core/mixins/modal'

export default {
  name: 'AdminBackupRestoreModal',
  mixins: [modal],
  props: {
    run: {
      type: Object,
      required: false,
      default: null,
    },
  },
  data() {
    return {
      target: '',
      error: '',
      loading: false,
      queued: '',
    }
  },
  methods: {
    async restore() {
      this.loading = true
      this.error = ''
      this.queued = ''
      try {
        const { data } = await BackupService(this.$client).restore(
          this.run.key,
          this.target
        )
        // The response carries the target with its password removed.
        this.queued = data.target
        this.target = ''
      } catch (error) {
        const detail = error.response?.data?.detail
        this.error = detail || this.$t('adminBackupRestore.failed')
      }
      this.loading = false
    },
  },
}
</script>
