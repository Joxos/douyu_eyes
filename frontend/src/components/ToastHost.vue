<template>
  <teleport to="body">
    <div class="toast-host" data-testid="toast-host" aria-live="polite" aria-atomic="true">
      <transition-group name="toast-fade" tag="div" class="toast-list">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          role="status"
          :class="`toast-${toast.type}`"
          data-testid="toast-message"
        >
          {{ toast.message }}
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { useToast } from '../composables/useToast'

const { toasts } = useToast()
</script>

<style scoped>
.toast-host {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 2000;
  pointer-events: none;
}

.toast-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast-item {
  pointer-events: auto;
  min-width: 180px;
  max-width: 320px;
  padding: 10px 14px;
  border-radius: 8px;
  color: #ffffff;
  background: var(--color-toast);
  box-shadow: var(--shadow-toast);
}

.toast-success {
  background: var(--color-toast-success);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.2s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
