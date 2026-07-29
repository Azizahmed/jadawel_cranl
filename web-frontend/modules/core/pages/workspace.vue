<template>
  <div v-if="workspaceExists">
    <div class="dashboard__header" ph-autocapture="dashboard-header">
      <div class="dashboard__header-left">
        <h1
          ref="contextLink"
          class="dashboard__workspace-name"
          @click="
            $refs.context.toggle($refs.contextLink, 'bottom', 'left', -14)
          "
        >
          <div class="dashboard__workspace-name-text">
            <Editable
              ref="rename"
              :value="selectedWorkspace.name"
              @change="renameWorkspace(selectedWorkspace, $event)"
            >
            </Editable>
          </div>
          <i class="dashboard__workspace-name-icon iconoir-nav-arrow-down"></i>
        </h1>
        <component
          :is="component"
          v-for="(component, index) in dashboardWorkspacePlanBadge"
          :key="index"
          :workspace="selectedWorkspace"
          :component-arguments="workspaceComponentArguments"
        ></component>
      </div>
      <WorkspaceContext
        ref="context"
        :workspace="selectedWorkspace"
        @rename="enableRename()"
      ></WorkspaceContext>
      <div class="dashboard__header-right">
        <component
          :is="component"
          v-for="(component, index) in dashboardWorkspaceRowUsageComponent"
          :key="index"
          :workspace="selectedWorkspace"
          :component-arguments="workspaceComponentArguments"
          @workspace-updated="workspaceUpdated($event)"
        ></component>
        <span
          v-if="canCreateCreateApplication"
          ref="createApplicationContextLink"
        >
          <Button
            icon="iconoir-plus"
            tag="a"
            @click="
              $refs.createApplicationContext.toggle(
                $refs.createApplicationContextLink
              )
            "
            >{{ $t('dashboard.addNew') }}</Button
          >
        </span>
      </div>
    </div>
    <div
      class="dashboard__scroll-container"
      ph-autocapture="dashboard-container"
    >
      <div class="dashboard__main">
        <DashboardVerifyEmail
          class="margin-top-0 margin-bottom-0"
        ></DashboardVerifyEmail>
        <WorkspaceInvitation
          v-for="invitation in workspaceInvitations"
          :key="'invitation-' + invitation.id"
          :invitation="invitation"
          class="margin-top-0 margin-bottom-0"
        ></WorkspaceInvitation>
        <div class="dashboard__wrapper">
          <ul
            v-if="orderedApplicationsInSelectedWorkspace.length"
            class="dashboard__applications"
          >
            <template
              v-for="application in orderedApplicationsInSelectedWorkspace"
            >
              <li
                v-if="getApplicationType(application).isVisible(application)"
                :key="application.id"
              >
                <DashboardApplication
                  :application="application"
                  :workspace="selectedWorkspace"
                  :stats="databaseStats[application.id] || null"
                  @click="selectApplication(application)"
                />
                <div class="dashboard__application-separator"></div>
              </li>
            </template>
          </ul>
          <div v-else class="dashboard__no-application">
            <img
              src="@baserow/modules/core/assets/images/empty_workspace_illustration.png"
              srcset="
                @baserow/modules/core/assets/images/empty_workspace_illustration@2x.png 2x
              "
            />
            <h4>{{ $t('dashboard.emptyWorkspace') }}</h4>
            <p v-if="canCreateCreateApplication">
              {{ $t('dashboard.emptyWorkspaceMessage') }}
            </p>
            <span
              v-if="canCreateCreateApplication"
              ref="createApplicationContextLink2"
            >
              <Button
                icon="iconoir-plus"
                tag="a"
                @click="
                  $refs.createApplicationContext.toggle(
                    $refs.createApplicationContextLink2
                  )
                "
                >{{ $t('dashboard.addNew') }}</Button
              >
            </span>
          </div>
        </div>
        <!--
          Jadawel fork: everything below the application list is secondary, and
          ordered by how much of it is about *this* workspace. The overview is
          the user's own data, so it comes first; templates and resource links
          are the same for everybody and sit under it.
        -->
        <DashboardOverview
          v-if="orderedApplicationsInSelectedWorkspace.length"
          :workspace="selectedWorkspace"
          :applications="orderedApplicationsInSelectedWorkspace"
          :stats="databaseStats"
          :activity="workspaceActivity"
        />

        <div class="dashboard__extras">
          <section
            v-if="canCreateCreateApplication"
            class="dashboard__suggested-templates"
          >
            <div class="dashboard__section-head">
              <h4 class="dashboard__section-title">
                {{ $t('dashboard.suggestedTemplates') }}
              </h4>
              <a
                class="dashboard__section-action"
                @click="$refs.templateModal.show()"
                >{{ $t('dashboard.browseAllTemplates') }}</a
              >
            </div>

            <div class="dashboard__suggested-templates-wrapper">
              <DashboardTemplateCard
                v-for="template in featuredTemplates"
                :key="template.slug"
                :name="template.name"
                :description="template.description"
                :icon="template.icon"
                @click="$refs.templateModal.show(template.slug)"
              />

              <DashboardTemplateCard
                view-more
                :name="$t('dashboard.browseTemplates')"
                @click="$refs.templateModal.show()"
              />
            </div>
          </section>

          <section
            v-if="resourceLinksComponents.length"
            class="dashboard__resources"
          >
            <h4 class="dashboard__section-title">
              {{ $t('dashboard.resources') }}
            </h4>
            <div class="dashboard__resources-wrapper">
              <component
                :is="component"
                v-for="(component, index) in resourceLinksComponents"
                :key="index"
              ></component>
            </div>
          </section>
        </div>
      </div>
      <CreateApplicationContext
        ref="createApplicationContext"
        :workspace="selectedWorkspace"
      >
      </CreateApplicationContext>
    </div>
    <component
      :is="component"
      v-for="(component, index) in dashboardHelpComponents"
      :key="index"
    ></component>
    <TemplateModal
      ref="templateModal"
      :workspace="selectedWorkspace"
    ></TemplateModal>
  </div>
</template>

<script setup>
import { ref, computed, unref, watchEffect } from 'vue'
import { useRoute, useRouter, useNuxtApp, createError } from '#app'
import { useHead, useAsyncData } from '#imports'

import WorkspaceContext from '@baserow/modules/core/components/workspace/WorkspaceContext'
import CreateApplicationContext from '@baserow/modules/core/components/application/CreateApplicationContext'
import DashboardApplication from '@baserow/modules/core/components/dashboard/DashboardApplication'
import WorkspaceInvitation from '@baserow/modules/core/components/workspace/WorkspaceInvitation'
import editWorkspace from '@baserow/modules/core/mixins/editWorkspace'
import DashboardVerifyEmail from '@baserow/modules/core/components/dashboard/DashboardVerifyEmail'
import DashboardOverview from '@baserow/modules/core/components/dashboard/DashboardOverview'
import DashboardTemplateCard from '@baserow/modules/core/components/dashboard/DashboardTemplateCard'
import TemplateModal from '@baserow/modules/core/components/template/TemplateModal'
import DatabaseStatsService from '@baserow/modules/arabase/services/databaseStats'
import WorkspaceActivityService from '@baserow/modules/arabase/services/workspaceActivity'

definePageMeta({
  layout: 'app',
  // Note: these middlewares must be explicitly listed because child pages
  // don't automatically inherit parent middleware in Nuxt 3's page meta
  middleware: [
    'settings',
    'authenticated',
    'impersonate',
    'workspacesAndApplications',
  ],
})

defineOptions({
  mixins: [editWorkspace],
})

const route = useRoute()
const router = useRouter()
const nuxtApp = useNuxtApp()
const { $store, $registry, $i18n, $hasPermission, $client } = nuxtApp

/**
 * Row / field / table counters keyed by database id.
 *
 * Fetched client-side, after the page has rendered, rather than awaited in
 * `useAsyncData` with the rest of the workspace payload. Row counting is a
 * COUNT(*) per table, so blocking the first paint on it would make the whole
 * page as slow as the largest workspace. The cards render immediately and fill
 * in their numbers when this resolves.
 */
const databaseStats = ref({})

/**
 * Rows created per day over the last month, or null until it resolves.
 *
 * Fetched separately from the counters above, for the same reason those are kept
 * out of the application payload: this query groups as well as counts, so a
 * workspace big enough to make it slow should not hold up the card numbers.
 */
const workspaceActivity = ref(null)

const ACTIVITY_DAYS = 30

/**
 * The templates offered on the home page, per interface language.
 *
 * Upstream hardcodes two English slugs here, which in an Arabic-first product
 * meant the home page advertised English templates and never surfaced the
 * Arabic ones this fork ships. The slugs still have to be named — there is no
 * "featured" flag on a template — but at least the right ones are named for the
 * language the user is reading. An unknown slug simply opens the picker with
 * nothing preselected, so a missing template degrades rather than breaks.
 */
const FEATURED_TEMPLATE_SLUGS = {
  ar: {
    projectManagement: 'arabic-project-management',
    performanceReview: 'arabic-performance-review',
  },
  en: {
    projectManagement: 'project-management',
    performanceReview: 'performance-reviews',
  },
}

const FEATURED_TEMPLATE_ICONS = {
  projectManagement: 'iconoir-task-list',
  performanceReview: 'iconoir-okrs',
}

// ----------------------------------------------------------------------------
// STATE
// ----------------------------------------------------------------------------
const selectedWorkspace = ref(null)
const workspaceComponentArguments = ref({})

const featuredTemplates = computed(() => {
  // `unref`, not `$i18n.locale` directly. In a `<script setup>` block the nuxt
  // app's `$i18n.locale` is a ref, while the same property read through the
  // options API is a plain string. Indexing with the ref silently misses and
  // falls through to English — and because `$i18n.t` resolves correctly
  // regardless, the cards render Arabic names pointing at English templates.
  const locale = unref($i18n.locale)
  const slugs = FEATURED_TEMPLATE_SLUGS[locale] || FEATURED_TEMPLATE_SLUGS.en
  return Object.entries(slugs).map(([key, slug]) => ({
    slug,
    icon: FEATURED_TEMPLATE_ICONS[key],
    name: $i18n.t(`dashboardTemplates.${key}.name`),
    description: $i18n.t(`dashboardTemplates.${key}.description`),
  }))
})

// refs used in template
const context = ref(null)
const contextLink = ref(null)
const createApplicationContext = ref(null)
const createApplicationContextLink = ref(null)
const createApplicationContextLink2 = ref(null)
const rename = ref(null)
const templateModal = ref(null)

async function fetchWorkspaceExtraData(workspace) {
  const plugins = Object.values($registry.getAll('plugin'))
  let mergedData = {
    selectedWorkspace: workspace,
    workspaceComponentArguments: { usageData: [] },
  }

  for (const p of plugins) {
    const workspaceData = await p.fetchAsyncDashboardData(nuxtApp, workspace.id)

    if (workspaceData) {
      mergedData = p.mergeDashboardData(mergedData, workspaceData)
    }
  }

  return mergedData
}

/**
 * Fetch all dashboard-related data for the current workspace.
 * `useAsyncData` now returns the data and we hydrate our refs from it.
 */
const {
  data: dashboardData,
  pending,
  error,
} = await useAsyncData(
  `current-workspace-${route.params.workspaceId}`,
  async () => {
    const workspaceId = parseInt(route.params.workspaceId, 10)

    let workspace
    try {
      workspace = await $store.dispatch('workspace/selectById', workspaceId)
    } catch (e) {
      throw createError({
        statusCode: 404,
        message: 'Workspace not found.',
      })
    }

    try {
      await $store.dispatch('auth/fetchWorkspaceInvitations')
      return await fetchWorkspaceExtraData(workspace)
    } catch {
      throw createError({
        statusCode: 400,
        message: 'Error loading dashboard.',
      })
    }
  }
)

if (error.value) {
  throw error.value
}

/**
 * Hydrate local refs from the async data.
 * Keeps your existing `selectedWorkspace` and `workspaceComponentArguments`
 * reactive and writable for later updates (e.g. `workspaceUpdated`).
 */
watchEffect(() => {
  if (!dashboardData.value) return
  selectedWorkspace.value = dashboardData.value.selectedWorkspace
  workspaceComponentArguments.value =
    dashboardData.value.workspaceComponentArguments
})

/**
 * Load the counters whenever the selected workspace changes.
 *
 * Failures are swallowed on purpose: the counters are a decoration on cards that
 * are already fully usable without them. A toast here would put an error in front
 * of the user for something they did not ask for and cannot act on.
 */
watchEffect(async () => {
  const workspace = selectedWorkspace.value
  if (!workspace) return

  databaseStats.value = {}
  workspaceActivity.value = null

  try {
    const { data } = await DatabaseStatsService($client).fetchAll(workspace.id)
    // Guard against a slower response for a workspace the user has since left.
    if (selectedWorkspace.value?.id === workspace.id) {
      databaseStats.value = data
    }
  } catch {
    databaseStats.value = {}
  }

  // Requested after the counters rather than alongside them: both walk every
  // table in the workspace, and the numbers on the cards are worth more to the
  // user than the chart further down the page.
  try {
    const { data } = await WorkspaceActivityService($client).fetch(
      workspace.id,
      ACTIVITY_DAYS
    )
    if (selectedWorkspace.value?.id === workspace.id) {
      workspaceActivity.value = data
    }
  } catch {
    workspaceActivity.value = null
  }
})

useHead(() => ({
  title: $i18n.t('dashboard.title'),
}))

const workspaceInvitations = computed(
  () => $store.getters['auth/getWorkspaceInvitations']
)

const getAllOfWorkspace = (ws) =>
  $store.getters['application/getAllOfWorkspace'](ws)

const dashboardHelpComponents = computed(() =>
  Object.values($registry.getAll('plugin'))
    .reduce(
      (components, plugin) =>
        components.concat(plugin.getDashboardHelpComponents()),
      []
    )
    .filter((c) => c !== null)
)

const dashboardWorkspaceRowUsageComponent = computed(() =>
  Object.values($registry.getAll('plugin'))
    .map((p) => p.getDashboardWorkspaceRowUsageComponent())
    .filter((c) => c !== null)
)

const dashboardWorkspacePlanBadge = computed(() =>
  Object.values($registry.getAll('plugin'))
    .map((p) => p.getDashboardWorkspacePlanBadge())
    .filter((c) => c !== null)
)

const resourceLinksComponents = computed(() =>
  Object.values($registry.getAll('plugin'))
    .map((p) => p.getDashboardResourceLinksComponent())
    .filter((c) => c !== null)
)

const orderedApplicationsInSelectedWorkspace = computed(() =>
  !selectedWorkspace.value
    ? []
    : getAllOfWorkspace(selectedWorkspace.value).sort(
        (a, b) => a.order - b.order
      )
)

const canCreateCreateApplication = computed(() => {
  if (!selectedWorkspace.value) return false
  return $hasPermission(
    'workspace.create_application',
    selectedWorkspace.value,
    selectedWorkspace.value.id
  )
})

/**
 * Check if the workspace exists, because if not, it doesn't make any sense to
 * render anything. This can happen when the workspace is a state where it's
 * deleted, for example.
 */
const workspaceExists = computed(() => {
  if (!selectedWorkspace.value) return false
  return $store.getters['workspace/getAll'].some(
    (w) => w.id === selectedWorkspace.value.id
  )
})

// ----------------------------------------------------------------------------
// METHODS
// ----------------------------------------------------------------------------
function getApplicationType(application) {
  return $registry.get('application', application.type)
}

function selectApplication(application) {
  const type = getApplicationType(application)
  const { $store, $i18n } = nuxtApp
  type.select(application, { $router: router, $store, $i18n })
}

async function workspaceUpdated(workspace) {
  const extraData = await fetchWorkspaceExtraData(workspace)
  workspaceComponentArguments.value = extraData.workspaceComponentArguments
}
</script>
