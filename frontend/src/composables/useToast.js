import { ref } from 'vue'

const toasts = ref([])
let nextToastId = 1

export const useToast = () => {
  const showToast = (message, options = {}) => {
    const duration = typeof options.duration === 'number' ? options.duration : 1800
    const type = options.type || 'success'
    const id = nextToastId
    nextToastId += 1

    toasts.value.push({ id, message, type })

    if (duration > 0) {
      setTimeout(() => {
        toasts.value = toasts.value.filter((toast) => toast.id !== id)
      }, duration)
    }

    return id
  }

  const dismissToast = (id) => {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }

  return {
    toasts,
    showToast,
    dismissToast,
  }
}
