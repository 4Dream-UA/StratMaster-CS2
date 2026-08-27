<template>
  <div class="image-upload-field">
    <input
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      type="text"
      :placeholder="placeholder"
      class="url-input"
    />
    <label class="upload-btn" :class="{ busy: uploading }">
      {{ uploading ? '…' : 'Upload' }}
      <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden @change="onFileChange" />
    </label>
    <p v-if="error" class="upload-err">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { uploadsAPI } from '../api/uploads'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Image URL' },
})
const emit = defineEmits(['update:modelValue'])

const uploading = ref(false)
const error = ref('')

async function onFileChange(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return

  uploading.value = true
  error.value = ''
  try {
    const res = await uploadsAPI.uploadImage(file)
    emit('update:modelValue', res.url)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Upload failed.'
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.image-upload-field {
  display: flex; align-items: center; gap: 6px;
  flex: 1; min-width: 0; position: relative;
}
.url-input {
  flex: 1; min-width: 0;
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  padding: 10px 12px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.url-input:focus { outline: none; border-color: var(--accent); }

.upload-btn {
  flex-shrink: 0; cursor: pointer;
  background: var(--bg-elevated); border: 1px solid var(--line); color: var(--text-dim);
  padding: 9px 13px; border-radius: 9px; font-size: 12px; font-weight: 700;
  transition: border-color .15s, color .15s;
  white-space: nowrap;
}
.upload-btn:hover { border-color: var(--accent); color: var(--accent); }
.upload-btn.busy { opacity: .6; cursor: wait; }

.upload-err {
  position: absolute; top: 100%; left: 0; margin-top: 4px;
  font-size: 11px; font-weight: 600; color: var(--danger);
  white-space: nowrap;
}
</style>
