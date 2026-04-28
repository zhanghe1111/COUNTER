<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'card' | 'list' | 'text'
  count?: number
}>(), {
  type: 'card',
  count: 3
})
</script>

<template>
  <div class="skeleton-wrapper">
    <div v-if="type === 'card'" class="skeleton-cards">
      <div v-for="i in count" :key="i" class="skeleton-card">
        <div class="skeleton-avatar" />
        <div class="skeleton-lines">
          <div class="skeleton-line w-60" />
          <div class="skeleton-line w-40" />
        </div>
      </div>
    </div>
    <div v-else-if="type === 'list'" class="skeleton-list">
      <div v-for="i in count" :key="i" class="skeleton-list-item">
        <div class="skeleton-line w-80" />
        <div class="skeleton-line w-30" />
      </div>
    </div>
    <div v-else class="skeleton-texts">
      <div v-for="i in count" :key="i" class="skeleton-line" :class="`w-${[80, 60, 90, 50, 70][i % 5]}`" />
    </div>
  </div>
</template>

<style scoped>
.skeleton-wrapper {
  width: 100%;
}

.skeleton-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--border-color);
  flex-shrink: 0;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.skeleton-texts {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 14px;
  background: var(--border-color);
  border-radius: 4px;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.skeleton-line.w-80 { width: 80%; }
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-40 { width: 40%; }
.skeleton-line.w-90 { width: 90%; }
.skeleton-line.w-30 { width: 30%; }
.skeleton-line.w-70 { width: 70%; }

@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 0.3; }
}
</style>
