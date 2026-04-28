<script setup lang="ts">
import { useToastStore } from '@/stores/toast'
import { Icon } from '@iconify/vue'

const toastStore = useToastStore()

const iconMap: Record<string, string> = {
  success: 'mdi:check-circle',
  error: 'mdi:close-circle',
  warning: 'mdi:alert-circle',
  info: 'mdi:information'
}
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="toast-item"
        :class="toast.type"
      >
        <Icon :icon="iconMap[toast.type]" :width="20" />
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="toastStore.removeToast(toast.id)">
          <Icon icon="mdi:close" :width="16" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  max-width: 90vw;
  width: auto;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 10px;
  pointer-events: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  font-size: 0.85rem;
  backdrop-filter: blur(10px);
  min-width: 200px;
  max-width: 90vw;
}

.toast-item.success {
  background: rgba(78, 204, 163, 0.2);
  border: 1px solid rgba(78, 204, 163, 0.4);
  color: var(--success-color);
}

.toast-item.error {
  background: rgba(255, 107, 107, 0.2);
  border: 1px solid rgba(255, 107, 107, 0.4);
  color: var(--danger-color);
}

.toast-item.warning {
  background: rgba(255, 193, 7, 0.2);
  border: 1px solid rgba(255, 193, 7, 0.4);
  color: var(--warning-color);
}

.toast-item.info {
  background: rgba(0, 217, 255, 0.2);
  border: 1px solid rgba(0, 217, 255, 0.4);
  color: var(--info-color);
}

.toast-message {
  flex: 1;
  font-size: 0.85rem;
  line-height: 1.4;
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  opacity: 0.7;
  padding: 2px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.toast-close:hover {
  opacity: 1;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
