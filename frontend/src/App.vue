<script setup lang="ts">
import { RouterView } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
</script>

<template>
  <div id="app">
    <ToastContainer />
    <RouterView v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </RouterView>
  </div>
</template>

<style>
#app {
  width: 100%;
  min-height: 100vh;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
