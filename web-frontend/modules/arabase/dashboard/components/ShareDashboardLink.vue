<template>
  <div>
    <a
      ref="contextLink"
      class="header__filter-link"
      :class="{ 'active active--primary': isShared }"
      @click="$refs.context.toggle($refs.contextLink, 'bottom', 'left', 4)"
    >
      <i class="header__filter-icon iconoir-share-android"></i>
      <span class="header__filter-name">
        {{ $t('shareDashboardLink.shareDashboard') }}
      </span>
    </a>

    <Context ref="context" max-height-if-outside-viewport>
      <div class="view-sharing__content">
        <div v-if="loading" class="loading margin-auto"></div>

        <div
          v-else-if="!isShared"
          class="view-sharing__share-link view-sharing__share-link--scrollable"
        >
          <div class="view-sharing__share-link-title">
            {{ $t('shareDashboardLink.shareTitle') }}
          </div>
          <p class="view-sharing__share-link-description">
            {{ $t('shareDashboardLink.shareText') }}
          </p>
          <Error :error="error"></Error>
          <div class="view-sharing__share-link-options">
            <Button
              type="secondary"
              icon="jadawel-icon-share"
              :disabled="submitting"
              @click.stop="createLink"
            >
              {{ $t('shareDashboardLink.createLink') }}
            </Button>
          </div>
        </div>

        <div v-else class="view-sharing">
          <div class="view-sharing--scrollable">
            <div class="view-sharing__shared-link">
              <div class="view-sharing__shared-link-title">
                {{ $t('shareDashboardLink.sharedTitle') }}
              </div>
              <div class="view-sharing__shared-link-description">
                {{ $t('shareDashboardLink.sharedDescription') }}
              </div>
              <Error :error="error"></Error>

              <div class="view-sharing__shared-link-content">
                <div class="view-sharing__shared-link-box">{{ shareUrl }}</div>
                <a
                  v-tooltip="$t('shareDashboardLink.copyURL')"
                  class="view-sharing__shared-link-action"
                  @click="copyShareUrlToClipboard()"
                >
                  <i class="iconoir-copy" />
                  <Copied ref="copied"></Copied>
                </a>
                <a
                  v-tooltip="$t('shareDashboardLink.generateNewUrl')"
                  class="view-sharing__shared-link-action"
                  @click.prevent="$refs.rotateSlugModal.show()"
                >
                  <i class="iconoir-refresh-double" />
                </a>
              </div>

              <div class="view-sharing__shared-link-options">
                <div class="view-sharing__option">
                  <SwitchInput
                    small
                    :value="share.has_password"
                    @input="togglePassword"
                  >
                    <i
                      class="switch__icon view-sharing__option-icon"
                      :class="[
                        share.has_password ? 'iconoir-lock' : 'iconoir-globe',
                      ]"
                    />
                    <span>{{ $t(optionPasswordText) }}</span>
                  </SwitchInput>

                  <a
                    v-if="share.has_password"
                    class="view-sharing__option-change-password"
                    @click.stop="$refs.passwordModal.show()"
                  >
                    {{ $t('shareDashboardLink.changePassword') }}
                    <i class="iconoir-edit-pencil" />
                  </a>
                </div>
              </div>
            </div>
          </div>

          <div class="context__footer">
            <ButtonText icon="iconoir-cancel" @click.stop="disableLink">
              {{ $t('shareDashboardLink.disableLink') }}
            </ButtonText>
          </div>
        </div>
      </div>
    </Context>

    <DashboardRotateSlugModal
      ref="rotateSlugModal"
      :dashboard="dashboard"
      @rotated="share = $event"
    />
    <DashboardSharePasswordModal
      ref="passwordModal"
      :dashboard="dashboard"
      :change="share ? share.has_password : false"
      @updated="share = $event"
    />
  </div>
</template>

<script>
import error from '@jadawel/modules/core/mixins/error'
import { copyToClipboard } from '@jadawel/modules/database/utils/clipboard'
import DashboardShareService from '@jadawel/modules/arabase/services/dashboardShare'
import DashboardRotateSlugModal from '@jadawel/modules/arabase/dashboard/components/DashboardRotateSlugModal'
import DashboardSharePasswordModal from '@jadawel/modules/arabase/dashboard/components/DashboardSharePasswordModal'

export default {
  name: 'ShareDashboardLink',
  components: { DashboardRotateSlugModal, DashboardSharePasswordModal },
  mixins: [error],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      // `null` means "not shared". Loaded once, then kept in sync locally so
      // the menu never re-fetches while the user toggles options.
      share: null,
      loading: true,
      submitting: false,
    }
  },
  computed: {
    isShared() {
      return this.share !== null
    },
    shareUrl() {
      if (!this.share) {
        return ''
      }
      const baseUrl = this.$config.public.jadawelEmbeddedShareUrl.replace(
        /\/+$/,
        ''
      )
      const sharePath = this.$router
        .resolve({
          name: 'arabase-public-dashboard',
          params: { slug: this.share.slug },
        })
        .href.replace(/^\/+/, '')

      return `${baseUrl}/${sharePath}`
    },
    optionPasswordText() {
      return this.share && this.share.has_password
        ? 'shareDashboardLink.disablePassword'
        : 'shareDashboardLink.enablePassword'
    },
  },
  async mounted() {
    await this.fetchShare()
  },
  methods: {
    async fetchShare() {
      this.loading = true
      try {
        const { data } = await DashboardShareService(this.$client).get(
          this.dashboard.id
        )
        this.share = data
      } catch (e) {
        this.handleError(e, 'dashboard')
      }
      this.loading = false
    },
    async createLink() {
      this.hideError()
      this.submitting = true
      try {
        const { data } = await DashboardShareService(this.$client).create(
          this.dashboard.id
        )
        this.share = data
      } catch (e) {
        this.handleError(e, 'dashboard')
      }
      this.submitting = false
    },
    async disableLink() {
      this.hideError()
      try {
        await DashboardShareService(this.$client).delete(this.dashboard.id)
        this.share = null
      } catch (e) {
        this.handleError(e, 'dashboard')
      }
    },
    togglePassword() {
      if (this.share.has_password) {
        this.removePassword()
      } else {
        this.$refs.passwordModal.show()
      }
    },
    async removePassword() {
      this.hideError()
      try {
        const { data } = await DashboardShareService(this.$client).setPassword(
          this.dashboard.id,
          null
        )
        this.share = data
      } catch (e) {
        this.handleError(e, 'dashboard')
      }
    },
    copyShareUrlToClipboard() {
      copyToClipboard(this.shareUrl)
      this.$refs.copied.show()
    },
  },
}
</script>
