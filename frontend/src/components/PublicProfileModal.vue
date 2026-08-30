<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal profile-modal">
      <button class="modal-close" @click="$emit('close')">✕</button>

      <div v-if="loading" class="loading-row">Loading…</div>
      <template v-else-if="profile">
        <div class="profile-modal-head">
          <div class="profile-modal-avatar" :class="{ admin: profile.is_admin }">
            <img v-if="profile.avatar_url" :src="profile.avatar_url" alt="" />
            <span v-else>{{ (profile.username || profile.display_name || '?').charAt(0).toUpperCase() }}</span>
          </div>
          <h3>{{ profile.display_name || (profile.username ? '@' + profile.username : 'Player') }}</h3>
          <span v-if="profile.username && profile.display_name" class="profile-modal-sub">@{{ profile.username }}</span>
          <span v-if="profile.is_admin" class="admin-badge">ADMIN</span>
        </div>

        <div v-if="hasInfo" class="profile-modal-links">
          <button
            v-for="f in filledFields" :key="f.key" type="button" class="profile-modal-link"
            @click="copyValue(f.key, profile.profile_info[f.key])"
          >
            <span class="profile-modal-link-icon" v-html="f.icon"></span>
            <span class="profile-modal-link-label">{{ f.label }}</span>
            <span class="profile-modal-link-value">{{ profile.profile_info[f.key] }}</span>
            <span class="profile-modal-link-copy">{{ copiedKey === f.key ? 'Copied!' : 'Copy' }}</span>
          </button>
        </div>
        <p v-else class="favorites-placeholder">This player hasn't shared any contact info.</p>
      </template>
      <p v-else class="err">Could not load this profile.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { authAPI } from '../api/auth'

const props = defineProps({ userId: { type: String, required: true } })
defineEmits(['close'])

const profile = ref(null)
const loading = ref(true)

const FIELDS = [
  { key: 'location', label: 'Location', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M12 21s7-6.5 7-11.5A7 7 0 105 9.5C5 14.5 12 21 12 21z" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="9.5" r="2.4" stroke="currentColor" stroke-width="1.6"/></svg>' },
  { key: 'telegram', label: 'Telegram', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M21 4L2.5 11.3c-.9.35-.9 1.65.05 1.95l4.4 1.4 1.7 5.3c.3.9 1.4 1.1 2 .35l2.5-3 4.9 3.6c.85.6 2.05.15 2.3-.85L22.8 5.1c.25-1.05-.75-1.9-1.8-1.1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>' },
  { key: 'instagram', label: 'Instagram', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><rect x="3" y="3" width="18" height="18" rx="5" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.6"/><circle cx="17.5" cy="6.5" r="1.1" fill="currentColor"/></svg>' },
  { key: 'discord', label: 'Discord', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M6 8.5C8 7 10 6.5 12 6.5s4 .5 6 2M5 9c-1.5 3-2 6-1.5 9.5 2 1.5 4 2 4 2l1-2M19 9c1.5 3 2 6 1.5 9.5-2 1.5-4 2-4 2l-1-2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="9" cy="13.5" r="1.4" fill="currentColor"/><circle cx="15" cy="13.5" r="1.4" fill="currentColor"/></svg>' },
  { key: 'faceit', label: 'Faceit', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M12 2l8 4.5v11L12 22l-8-4.5v-11L12 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M9 12h6M12 9v6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
  { key: 'steam', label: 'Steam', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.5"/><circle cx="15.5" cy="9" r="2.3" stroke="currentColor" stroke-width="1.4"/><path d="M4.5 15l4 1.6a2.3 2.3 0 104-1.1l3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>' },
  { key: 'whatsapp', label: 'WhatsApp', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M4 20l1.4-4A8 8 0 1112 20a8 8 0 01-4-1.4L4 20z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>' },
  { key: 'twitch', label: 'Twitch', icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M5 3l-1.5 4v12h5V22l3-3h4l4.5-4.5V3H5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M13 8v4M17 8v4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>' },
]

const filledFields = computed(() => {
  if (!profile.value?.profile_info) return []
  return FIELDS.filter(f => profile.value.profile_info[f.key])
})
const hasInfo = computed(() => filledFields.value.length > 0)

const copiedKey = ref(null)
function copyValue(key, value) {
  navigator.clipboard?.writeText(value).then(() => {
    copiedKey.value = key
    setTimeout(() => { if (copiedKey.value === key) copiedKey.value = null }, 1600)
  }).catch(() => {})
}

onMounted(async () => {
  try {
    profile.value = await authAPI.getPublicProfile(props.userId)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; z-index: 600;
  background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(4px); overflow-y: auto;
}
.modal {
  position: relative; width: 100%; max-width: 360px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 28px 22px 22px; margin: auto;
}
.modal-close {
  position: absolute; top: 14px; right: 14px; width: 28px; height: 28px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.modal-close:hover { border-color: var(--accent); color: var(--accent); }
.loading-row { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }
.err { color: var(--danger); font-size: 13px; text-align: center; }

.profile-modal-head { display: flex; flex-direction: column; align-items: center; text-align: center; margin-bottom: 18px; }
.profile-modal-avatar {
  width: 72px; height: 72px; border-radius: 50%; margin-bottom: 10px;
  background: var(--bg); display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 800; color: var(--text-dim); overflow: hidden;
}
.profile-modal-avatar.admin { box-shadow: 0 0 0 3px var(--danger); }
.profile-modal-avatar img { width: 100%; height: 100%; object-fit: cover; }
.profile-modal-head h3 { font-size: 17px; font-weight: 800; color: var(--text); }
.profile-modal-sub { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
.admin-badge {
  margin-top: 8px; padding: 2px 8px; border-radius: 6px;
  background: rgba(255,80,80,0.15); border: 1px solid rgba(255,80,80,0.4);
  color: var(--danger); font-size: 9px; font-weight: 800; letter-spacing: .04em;
}

.profile-modal-links { display: flex; flex-direction: column; gap: 8px; }
.profile-modal-link {
  display: flex; align-items: center; gap: 10px; width: 100%;
  background: var(--bg); border: 1px solid transparent; border-radius: 9px; padding: 9px 12px;
  cursor: pointer; font-family: inherit; text-align: left; transition: border-color .15s;
}
.profile-modal-link:hover { border-color: var(--accent); }
.profile-modal-link-icon { color: var(--accent); flex-shrink: 0; display: flex; }
.profile-modal-link-label { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: var(--text-dim); flex-shrink: 0; width: 66px; }
.profile-modal-link-value { font-size: 12.5px; color: var(--text); word-break: break-word; flex: 1; min-width: 0; }
.profile-modal-link-copy {
  font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em;
  color: var(--text-dim); flex-shrink: 0;
}
.profile-modal-link:hover .profile-modal-link-copy { color: var(--accent); }

.favorites-placeholder { font-size: 12.5px; color: var(--text-dim); text-align: center; padding: 12px 0; }
</style>
