<template>
  <div v-if="roleUID" class="highest-role-field">
    {{ roleName }}
    <Badge v-if="roleIsBillable" color="cyan" class="margin-left-1"
      >{{ $t('highestPaidRoleField.billable') }}
    </Badge>
  </div>
</template>

<script>
export default {
  name: 'HighestPaidRoleField',
  props: {
    row: {
      required: true,
      type: Object,
    },
    column: {
      required: true,
      type: Object,
    },
  },
  computed: {
    roleUID() {
      return this.row[this.column.key]
    },
    roleName() {
      return this.role ? this.role.getName() : ''
    },
    roleIsBillable() {
      return this.role ? this.role.getIsBillable() : ''
    },
    role() {
      return Object.values(this.$registry.getAll('roles')).find(
        (role) => role.getUid() === this.roleUID
      )
    },
  },
}
</script>
