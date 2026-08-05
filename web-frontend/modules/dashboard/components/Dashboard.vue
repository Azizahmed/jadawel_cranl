<template>
  <div class="dashboard-app">
    <DashboardHeader :dashboard="dashboard" :store-prefix="storePrefix" />
    <DashboardContent :dashboard="dashboard" :store-prefix="storePrefix" />
  </div>
</template>

<script>
import DashboardHeader from '@jadawel/modules/dashboard/components/DashboardHeader'
import DashboardContent from '@jadawel/modules/dashboard/components/DashboardContent'

export default {
  name: 'Dashboard',
  components: { DashboardHeader, DashboardContent },
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    storePrefix: {
      type: String,
      required: false,
      default: '',
    },
  },
}
</script>
