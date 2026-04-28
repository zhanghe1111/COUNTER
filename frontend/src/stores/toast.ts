import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToastMessage {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<ToastMessage[]>([])
  let nextId = 0

  const addToast = (type: ToastMessage['type'], message: string, duration = 3000) => {
    const id = nextId++
    toasts.value.push({ id, type, message, duration })
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }

  const removeToast = (id: number) => {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      toasts.value.splice(idx, 1)
    }
  }

  const success = (msg: string) => addToast('success', msg)
  const error = (msg: string) => addToast('error', msg, 4000)
  const warning = (msg: string) => addToast('warning', msg, 3500)
  const info = (msg: string) => addToast('info', msg)

  return { toasts, addToast, removeToast, success, error, warning, info }
})
