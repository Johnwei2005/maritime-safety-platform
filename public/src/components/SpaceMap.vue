<template>
  <div class="space-map">
    <h2>空间模型展示</h2>
    <div>
      <!-- 展示空间分割、拓扑、通风率等信息 -->
      <pre>{{ spaceData }}</pre>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex'
export default {
  name: 'SpaceMap',
  computed: {
    ...mapState({
      spaceData: state => state.space
    })
  },
  mounted() {
    this.$store.dispatch('space/fetchSpaceData')
  }
}
</script>

<style scoped>
.space-map {
  padding: 1rem;
}
</style>
