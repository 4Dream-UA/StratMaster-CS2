<template>
  <nav v-if="totalPages > 1" class="pagination" aria-label="Pagination">
    <button
      type="button" class="page-btn nav-btn"
      :disabled="page <= 1"
      @click="go(page - 1)"
      aria-label="Previous page"
    >‹</button>

    <button
      v-for="p in pageNumbers" :key="p === '…' ? `dots-${Math.random()}` : p"
      type="button"
      class="page-btn"
      :class="{ active: p === page, dots: p === '…' }"
      :disabled="p === '…'"
      @click="p !== '…' && go(p)"
    >{{ p }}</button>

    <button
      type="button" class="page-btn nav-btn"
      :disabled="page >= totalPages"
      @click="go(page + 1)"
      aria-label="Next page"
    >›</button>
  </nav>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  total:    { type: Number, required: true },
  page:     { type: Number, required: true },      // 1-indexed
  pageSize: { type: Number, default: 5 },
})
const emit = defineEmits(['update:page'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

// Windowed page list with ellipsis: always show first, last, current ± 1.
const pageNumbers = computed(() => {
  const total = totalPages.value
  const current = props.page
  const pages = []
  const add = (p) => pages.push(p)

  const window = new Set([1, total, current - 1, current, current + 1].filter(p => p >= 1 && p <= total))
  const sorted = [...window].sort((a, b) => a - b)

  let prev = null
  for (const p of sorted) {
    if (prev !== null && p - prev > 1) add('…')
    add(p)
    prev = p
  }
  return pages
})

function go(p) {
  if (p < 1 || p > totalPages.value || p === props.page) return
  emit('update:page', p)
}
</script>

<style scoped>
.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; margin-top: 28px; flex-wrap: wrap;
}
.page-btn {
  min-width: 34px; height: 34px; padding: 0 8px;
  border-radius: 8px; border: 1.5px solid var(--line);
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); color: var(--text-dim);
  font-size: 13px; font-weight: 600; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.15);
  transition: border-color .18s, color .18s, background .18s, transform .15s, box-shadow .15s;
}
@media (hover: hover) and (pointer: fine) {
  .page-btn:not(:disabled):hover {
    border-color: var(--accent); color: var(--accent);
    box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px);
  }
}
.page-btn:active:not(:disabled) { transform: translateY(0); }
.page-btn.active {
  background: rgba(255,154,0,.14); border-color: var(--accent); color: var(--accent);
  box-shadow: 0 0 0 1px rgba(255,154,0,.25) inset;
}
.page-btn.dots { border-color: transparent; background: none; box-shadow: none; cursor: default; }
.page-btn:disabled:not(.dots) { opacity: .4; cursor: not-allowed; box-shadow: none; }
.nav-btn { font-size: 16px; font-weight: 700; }
</style>
