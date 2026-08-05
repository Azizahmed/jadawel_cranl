<template>
  <div class="sidebar__section sidebar__section--scrollable">
    <div class="sidebar__section-scrollable">
      <div
        class="sidebar__section-scrollable-inner"
        data-highlight="applications"
      >
        <ul v-if="pendingJobs[null].length" class="tree">
          <component
            :is="getPendingJobComponent(job)"
            v-for="job in pendingJobs[null]"
            :key="job.id"
            :job="job"
          >
          </component>
        </ul>
        <!--
          Jadawel: one list instead of a heading, a `+` and a separator per
          application type. Four groups of one or two items each spent more
          vertical space on chrome than on content, and the headings were the
          same colour and weight as the rows beneath them, so they did not read
          as headings anyway. Every type is still creatable from the "add new"
          menu at the foot of the panel, which also covers templates and import.
        -->
        <ul class="tree">
          <component
            :is="getApplicationComponent(application)"
            v-for="application in orderedApplications"
            :key="application.id"
            v-sortable="{
              id: application.id,
              update: orderApplications,
              handle: '[data-sortable-handle]',
              marginTop: -1.5,
              enabled: $hasPermission(
                'workspace.order_applications',
                selectedWorkspace,
                selectedWorkspace.id
              ),
            }"
            :application="application"
            :pending-jobs="pendingJobs[application.type]"
            :workspace="selectedWorkspace"
          ></component>
        </ul>
        <ul v-if="typedPendingJobs.length" class="tree">
          <component
            :is="getPendingJobComponent(job)"
            v-for="job in typedPendingJobs"
            :key="job.id"
            :job="job"
          >
          </component>
        </ul>
      </div>
    </div>
    <div
      v-if="
        $hasPermission(
          'workspace.create_application',
          selectedWorkspace,
          selectedWorkspace.id
        )
      "
      class="sidebar__new-wrapper sidebar__new-wrapper--separator"
      data-highlight="create-new"
    >
      <a
        ref="createApplicationContextLink"
        class="sidebar__new"
        @click="
          $refs.createApplicationContext.toggle(
            $refs.createApplicationContextLink
          )
        "
      >
        <i class="sidebar__new-icon iconoir-plus"></i>
        {{ $t('action.createNew') }}...
      </a>
    </div>
    <CreateApplicationContext
      ref="createApplicationContext"
      :workspace="selectedWorkspace"
    ></CreateApplicationContext>
  </div>
</template>

<script>
import { notifyIf } from '@jadawel/modules/core/utils/error'
import CreateApplicationContext from '@jadawel/modules/core/components/application/CreateApplicationContext'

export default {
  name: 'SidebarWithWorkspace',
  components: { CreateApplicationContext },
  props: {
    applications: {
      type: Array,
      required: true,
    },
    selectedWorkspace: {
      type: Object,
      required: true,
    },
  },
  computed: {
    /**
     * Every application in the selected workspace, in one list.
     *
     * Sorting on `order` alone is correct because `Application.order` is
     * allocated per workspace, not per type — the grouped rendering this
     * replaced was re-sorting the same workspace-wide sequence inside each
     * type. As a side effect a database and a dashboard can now be dragged
     * past each other, which the backend already accepted.
     */
    orderedApplications() {
      return this.applications
        .filter((application) => {
          if (application.workspace.id !== this.selectedWorkspace.id) {
            return false
          }
          // An application whose type is not registered in this build cannot be
          // rendered; skipping it here keeps the sidebar alive rather than
          // throwing out of the v-for.
          if (!this.$registry.exists('application', application.type)) {
            return false
          }
          return this.$registry
            .get('application', application.type)
            .isVisible(application)
        })
        .sort((a, b) => a.order - b.order)
    },
    /**
     * Pending jobs that belong to an application type rather than to the
     * workspace as a whole. They used to render under their type's heading;
     * with one list they all collect below the applications.
     */
    typedPendingJobs() {
      return Object.entries(this.pendingJobs)
        .filter(([type]) => type !== 'null')
        .flatMap(([, jobs]) => jobs)
    },
    pendingJobs() {
      const grouped = { null: [] }
      Object.values(this.$registry.getAll('application')).forEach(
        (applicationType) => {
          grouped[applicationType.getType()] = []
        }
      )
      this.$store.getters['job/getAll'].forEach((job) => {
        const jobType = this.$registry.get('job', job.type)
        if (jobType.isJobPartOfWorkspace(job, this.selectedWorkspace)) {
          grouped[jobType.getSidebarApplicationTypeLocation(job)].push(job)
        }
      })
      return grouped
    },
  },
  methods: {
    getApplicationComponent(application) {
      return this.$registry
        .get('application', application.type)
        .getSidebarComponent()
    },
    getPendingJobComponent(job) {
      return this.$registry.get('job', job.type).getSidebarComponent()
    },
    async orderApplications(order, oldOrder) {
      try {
        await this.$store.dispatch('application/order', {
          workspace: this.selectedWorkspace,
          order,
          oldOrder,
        })
      } catch (error) {
        notifyIf(error, 'application')
      }
    },
  },
}
</script>
