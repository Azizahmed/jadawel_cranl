<template>
  <!--
    Replaces the upstream TemplateCard on this page. That one is a large preview
    image with a caption underneath: the art is generic, it does not say what the
    template contains, and its "view more" variant renders as an empty white box
    that reads like a failed image load. This card leads with an icon in the
    brand tint and spends its space on the description instead.
  -->
  <a
    v-if="!viewMore"
    class="dashboard__template-card"
    @click="$emit('click')"
  >
    <span class="dashboard__template-card-icon">
      <i :class="icon"></i>
    </span>
    <span class="dashboard__template-card-name">{{ name }}</span>
    <span class="dashboard__template-card-description">{{ description }}</span>
  </a>

  <a v-else class="dashboard__template-card dashboard__template-card--more" @click="$emit('click')">
    <i class="dashboard__template-card-more-icon iconoir-plus"></i>
    <span class="dashboard__template-card-name">{{ name }}</span>
  </a>
</template>

<script>
export default {
  name: 'DashboardTemplateCard',
  props: {
    name: {
      type: String,
      required: true,
    },
    description: {
      type: String,
      required: false,
      default: '',
    },
    icon: {
      type: String,
      required: false,
      default: 'iconoir-page',
    },
    viewMore: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['click'],
}
</script>
