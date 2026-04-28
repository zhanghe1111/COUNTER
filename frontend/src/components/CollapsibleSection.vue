<script setup lang="ts">
import { ref } from 'vue'
import { Icon } from '@iconify/vue'

const props = withDefaults(defineProps<{
  title: string
  icon?: string
  defaultOpen?: boolean
  badge?: string | number
  badgeType?: 'info' | 'success' | 'warning' | 'danger'
}>(), {
  defaultOpen: false,
  badgeType: 'info'
})

const isOpen = ref(props.defaultOpen)

const toggle = () => {
  isOpen.value = !isOpen.value
}
</script>

<template>
  <div class="collapsible-section" :class="{ 'is-open': isOpen }">
    <button class="section-header" @click="toggle">
      <div class="header-left">
        <Icon v-if="icon" :icon="icon" :width="18" class="header-icon" />
        <span class="header-title">{{ title }}</span>
        <span v-if="badge !== undefined" class="header-badge" :class="badgeType">{{ badge }}</span>
      </div>
      <div class="header-right">
        <Icon
          icon="mdi:chevron-down"
          :width="20"
          class="chevron-icon"
          :class="{ rotated: isOpen }"
        />
      </div>
    </button>
    <Transition name="collapse">
      <div v-show="isOpen" class="section-body">
        <div class="section-content">
          <slot />
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.collapsible-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--transition-normal);
}

.collapsible-section.is-open {
  border-color: rgba(43, 110, 240, 0.25);
}

.section-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.section-header:hover {
  background: var(--bg-hover);
}

.section-header:active {
  background: rgba(255, 255, 255, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.header-icon {
  flex-shrink: 0;
  opacity: 0.7;
}

.header-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-badge {
  font-size: 0.7rem;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

.header-badge.info {
  background: rgba(0, 217, 255, 0.2);
  color: var(--info-color);
}

.header-badge.success {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.header-badge.warning {
  background: rgba(255, 193, 7, 0.2);
  color: var(--warning-color);
}

.header-badge.danger {
  background: rgba(240, 72, 72, 0.15);
  color: var(--danger-color);
}

.header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.chevron-icon {
  transition: transform var(--transition-normal);
  opacity: 0.5;
}

.chevron-icon.rotated {
  transform: rotate(180deg);
  opacity: 0.8;
}

.section-body {
  overflow: hidden;
}

.section-content {
  padding: 0 16px 14px;
}

.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.25s ease;
  max-height: 500px;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
