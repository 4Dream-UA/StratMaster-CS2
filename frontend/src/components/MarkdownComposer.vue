<template>
  <div class="md-composer">
    <div class="md-toolbar">
      <button type="button" class="md-tool-btn" title="Bold" @click="wrapSelection('**')"><strong>B</strong></button>
      <button type="button" class="md-tool-btn" title="Italic" @click="wrapSelection('*')"><em>I</em></button>
      <button type="button" class="md-tool-btn" title="Code" @click="wrapSelection('`')">{{ '</>' }}</button>
      <label class="md-tool-btn md-image-btn" :class="{ busy: uploading }" title="Insert image">
        <span v-if="uploading">…</span>
        <ImageIcon v-else :size="13" />
        <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden @change="onImageChange" />
      </label>
      <button type="button" class="md-tool-btn md-preview-toggle" :class="{ active: previewOn }" @click="previewOn = !previewOn">
        {{ previewOn ? 'Write' : 'Preview' }}
      </button>
    </div>

    <textarea
      v-if="!previewOn" ref="textareaRef"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      :rows="rows" :placeholder="placeholder" class="md-textarea"
    ></textarea>
    <div v-else class="md-preview" v-html="renderMarkdown(modelValue) || '<span class=\'md-preview-empty\'>Nothing to preview yet.</span>'"></div>

    <p v-if="uploadError" class="md-error">{{ uploadError }}</p>
  </div>
</template>

<script setup>
import { ref, h } from 'vue'
import { forumAPI } from '../api/forum'
import { renderMarkdown } from '../utils/markdown'

const ImageIcon = {
  props: { size: { type: Number, default: 14 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none' }, [
      h('rect', { x: 3.5, y: 4.5, width: 17, height: 15, rx: 2, stroke: 'currentColor', 'stroke-width': 1.6 }),
      h('circle', { cx: 8.5, cy: 9.5, r: 1.5, stroke: 'currentColor', 'stroke-width': 1.4 }),
      h('path', { d: 'M4 16l5-4.5 3.5 3L16 11l4 4.5', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
    ])
  },
}

const props = defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: Number, default: 4 },
  placeholder: { type: String, default: "Write something… supports **bold**, *italic*, `code`" },
})
const emit = defineEmits(['update:modelValue'])

const textareaRef = ref(null)
const previewOn = ref(false)
const uploading = ref(false)
const uploadError = ref('')

function wrapSelection(marker) {
  const el = textareaRef.value
  if (!el) return
  const { selectionStart: start, selectionEnd: end } = el
  const text = props.modelValue
  const selected = text.slice(start, end) || 'text'
  const next = text.slice(0, start) + marker + selected + marker + text.slice(end)
  emit('update:modelValue', next)
  // Restore focus + selection after Vue re-renders the (now-changed) value.
  requestAnimationFrame(() => {
    el.focus()
    el.setSelectionRange(start + marker.length, start + marker.length + selected.length)
  })
}

async function onImageChange(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return

  uploading.value = true
  uploadError.value = ''
  try {
    const res = await forumAPI.uploadImage(file)
    const insert = `\n![image](${res.url})\n`
    emit('update:modelValue', props.modelValue + insert)
  } catch (err) {
    uploadError.value = err.response?.data?.detail || 'Image upload failed.'
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.md-composer { display: flex; flex-direction: column; gap: 6px; }

.md-toolbar { display: flex; align-items: center; gap: 4px; }
.md-tool-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  width: 28px; height: 28px; border-radius: 6px; font-size: 12px; font-weight: 700;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: border-color .15s, color .15s;
}
.md-tool-btn:hover { border-color: var(--accent); color: var(--accent); }
.md-image-btn { width: auto; padding: 0 8px; }
.md-image-btn.busy { opacity: .6; cursor: wait; }
.md-preview-toggle { width: auto; padding: 0 10px; margin-left: auto; font-size: 11px; text-transform: uppercase; letter-spacing: .03em; }
.md-preview-toggle.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.1); }

.md-textarea {
  width: 100%; padding: 10px 12px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  color: var(--text); font-size: 13.5px; font-family: inherit; resize: vertical;
}
.md-textarea:focus { outline: none; border-color: var(--accent); }

.md-preview {
  min-height: 80px; padding: 10px 12px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  color: var(--text); font-size: 13.5px; line-height: 1.6; white-space: pre-wrap;
}
.md-preview-empty { color: var(--text-dim); font-style: italic; }
.md-preview :deep(.md-img) { max-width: 100%; border-radius: 8px; margin: 6px 0; display: block; }
.md-preview :deep(a) { color: var(--accent); }
.md-preview :deep(code) { background: var(--bg-elevated); padding: 1px 5px; border-radius: 4px; font-size: 12px; }

.md-error { color: var(--danger); font-size: 11.5px; font-weight: 600; margin: 0; }
</style>
