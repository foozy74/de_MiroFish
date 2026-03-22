<template>
  <div class="tenant-settings">
    <header class="page-header">
      <button class="back-btn" @click="$router.back()">← Zurück</button>
      <div class="header-info">
        <h1 class="page-title">Einstellungen</h1>
        <span v-if="tenant" class="plan-badge" :class="`plan-${tenant.plan}`">
          {{ tenant.plan }}
        </span>
      </div>
      <p v-if="tenant" class="org-slug">{{ tenant.display_name }}</p>
    </header>

    <!-- Loading / Error -->
    <div v-if="loading" class="state-placeholder">Laden…</div>
    <div v-else-if="error" class="state-error">{{ error }}</div>

    <template v-else>
      <!-- ─── Verbrauch ──────────────────────────────────────── -->
      <section class="card">
        <h2 class="card-title">Monatlicher Verbrauch</h2>
        <div v-if="usage.length === 0" class="empty-hint">
          Noch keine Verbrauchsdaten vorhanden.
        </div>
        <div v-else class="usage-list">
          <div
            v-for="u in usage"
            :key="`${u.service}-${u.metric}`"
            class="usage-row"
          >
            <div class="usage-meta">
              <span class="usage-label">{{ serviceLabel(u.service) }} · {{ metricLabel(u.metric) }}</span>
              <span class="usage-count">
                {{ u.current }}
                <span class="usage-limit" v-if="u.limit === -1">/ ∞</span>
                <span class="usage-limit" v-else>/ {{ u.limit }}</span>
              </span>
            </div>
            <div v-if="u.limit !== -1" class="progress-track">
              <div
                class="progress-bar"
                :class="barClass(u.current, u.limit)"
                :style="{ width: `${pct(u.current, u.limit)}%` }"
              />
            </div>
            <div v-else class="progress-track progress-unlimited" />
          </div>
        </div>
      </section>

      <!-- ─── API-Keys ────────────────────────────────────────── -->
      <section class="card">
        <h2 class="card-title">API-Keys</h2>

        <!-- Vorhandene Keys -->
        <div v-if="keys.length > 0" class="key-list">
          <div v-for="k in keys" :key="k.key_name" class="key-row">
            <div class="key-info">
              <code class="key-name">{{ k.key_name }}</code>
              <span class="key-masked">{{ k.masked }}</span>
            </div>
            <button
              class="btn-icon btn-delete"
              :disabled="deleting === k.key_name"
              @click="deleteKey(k.key_name)"
              title="Löschen"
            >
              {{ deleting === k.key_name ? '…' : '×' }}
            </button>
          </div>
        </div>
        <p v-else class="empty-hint">Noch keine Keys gespeichert.</p>

        <!-- Neuen Key hinzufügen -->
        <div class="add-key-form">
          <h3 class="form-title">Key hinzufügen / ändern</h3>
          <div class="form-row">
            <select v-model="newKeyName" class="select-key">
              <option value="" disabled>Key auswählen…</option>
              <option v-for="k in ALLOWED_KEYS" :key="k" :value="k">{{ k }}</option>
            </select>
          </div>
          <div class="form-row">
            <input
              v-model="newKeyValue"
              type="password"
              class="input-value"
              placeholder="Wert eingeben…"
              autocomplete="off"
            />
          </div>
          <div v-if="saveError" class="form-error">{{ saveError }}</div>
          <button
            class="btn-save"
            :disabled="saving || !newKeyName || !newKeyValue"
            @click="saveKey"
          >
            {{ saving ? 'Speichern…' : 'Speichern' }}
          </button>
        </div>
      </section>

      <!-- Feedback -->
      <transition name="toast">
        <div v-if="toast" class="toast" :class="`toast-${toast.type}`">
          {{ toast.msg }}
        </div>
      </transition>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

const ALLOWED_KEYS = ['LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL_NAME', 'ZEP_API_KEY']

// ─── State ────────────────────────────────────────────────
const loading = ref(true)
const error   = ref(null)
const tenant  = ref(null)
const keys    = ref([])
const usage   = ref([])

const newKeyName  = ref('')
const newKeyValue = ref('')
const saving      = ref(false)
const saveError   = ref(null)
const deleting    = ref(null)
const toast       = ref(null)

// ─── Helpers ─────────────────────────────────────────────
function getAuthHeader() {
  // Clerk stellt den JWT als Session-Cookie bereit; alternativ kann
  // `window.Clerk?.session?.getToken()` genutzt werden.
  const token = localStorage.getItem('clerk_session_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function serviceLabel(service) {
  return service === 'bettafish' ? 'BettaFish' : 'MiroFish'
}

function metricLabel(metric) {
  const labels = { reports_generated: 'Berichte', simulations_run: 'Simulationen' }
  return labels[metric] ?? metric
}

function pct(current, limit) {
  if (!limit || limit <= 0) return 0
  return Math.min(Math.round((current / limit) * 100), 100)
}

function barClass(current, limit) {
  const p = pct(current, limit)
  if (p >= 90) return 'bar-red'
  if (p >= 70) return 'bar-yellow'
  return 'bar-green'
}

function showToast(msg, type = 'success') {
  toast.value = { msg, type }
  setTimeout(() => { toast.value = null }, 3000)
}

// ─── Datenladen ───────────────────────────────────────────
async function loadInfo() {
  loading.value = true
  error.value   = null
  try {
    const res = await fetch(`${API_BASE}/tenant/info`, {
      headers: { ...getAuthHeader() },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    tenant.value = data.tenant
    keys.value   = data.keys   ?? []
    usage.value  = data.usage  ?? []
  } catch (e) {
    error.value = `Laden fehlgeschlagen: ${e.message}`
  } finally {
    loading.value = false
  }
}

// ─── Key speichern ────────────────────────────────────────
async function saveKey() {
  saveError.value = null
  saving.value    = true
  try {
    const res = await fetch(`${API_BASE}/tenant/keys`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body:    JSON.stringify({ key_name: newKeyName.value, value: newKeyValue.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      saveError.value = data.error ?? 'Unbekannter Fehler'
      return
    }
    newKeyName.value  = ''
    newKeyValue.value = ''
    showToast('Key gespeichert.')
    await loadInfo()
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

// ─── Key löschen ─────────────────────────────────────────
async function deleteKey(keyName) {
  deleting.value = keyName
  try {
    const res = await fetch(`${API_BASE}/tenant/keys/${encodeURIComponent(keyName)}`, {
      method:  'DELETE',
      headers: { ...getAuthHeader() },
    })
    if (!res.ok) {
      const data = await res.json()
      showToast(data.error ?? 'Löschen fehlgeschlagen', 'error')
      return
    }
    showToast('Key entfernt.')
    await loadInfo()
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    deleting.value = null
  }
}

onMounted(loadInfo)
</script>

<style scoped>
.tenant-settings {
  max-width: 680px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  color: #e5e7eb;
  font-family: var(--font-sans, system-ui, sans-serif);
}

/* Header */
.page-header   { margin-bottom: 2rem; }
.back-btn      { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 0.875rem; padding: 0 0 0.5rem; }
.back-btn:hover { color: #e5e7eb; }
.header-info   { display: flex; align-items: center; gap: 0.75rem; }
.page-title    { font-size: 1.5rem; font-weight: 600; color: #fff; margin: 0; }
.org-slug      { font-size: 0.8125rem; color: #6b7280; margin: 0.25rem 0 0; }

/* Plan-Badge */
.plan-badge         { font-size: 0.6875rem; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 600; text-transform: uppercase; }
.plan-free          { background: rgba(107,114,128,.2); color: #9ca3af; }
.plan-starter       { background: rgba(59,130,246,.2); color: #93c5fd; }
.plan-pro           { background: rgba(20,184,166,.2); color: #5eead4; }
.plan-enterprise    { background: rgba(168,85,247,.2); color: #d8b4fe; }

/* Karten */
.card        { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.1); border-radius: 0.75rem; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; }
.card-title  { font-size: 0.875rem; font-weight: 500; color: #d1d5db; margin: 0 0 1rem; }

/* Usage */
.usage-list   { display: flex; flex-direction: column; gap: 0.875rem; }
.usage-row    { }
.usage-meta   { display: flex; justify-content: space-between; margin-bottom: 0.3rem; }
.usage-label  { font-size: 0.75rem; color: #9ca3af; }
.usage-count  { font-size: 0.75rem; color: #e5e7eb; }
.usage-limit  { color: #4b5563; }
.progress-track     { height: 5px; border-radius: 9999px; background: rgba(255,255,255,.08); overflow: hidden; }
.progress-unlimited { background: rgba(168,85,247,.15); }
.progress-bar       { height: 100%; border-radius: 9999px; transition: width 0.4s; }
.bar-green  { background: #14b8a6; }
.bar-yellow { background: #eab308; }
.bar-red    { background: #ef4444; }

/* Keys */
.key-list     { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.25rem; }
.key-row      { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.07); border-radius: 0.5rem; padding: 0.6rem 0.875rem; }
.key-info     { display: flex; align-items: center; gap: 0.75rem; }
.key-name     { font-size: 0.75rem; color: #9ca3af; }
.key-masked   { font-size: 0.75rem; color: #4b5563; font-family: monospace; }
.btn-icon     { background: none; border: none; cursor: pointer; font-size: 1rem; line-height: 1; padding: 0.25rem 0.4rem; border-radius: 0.375rem; }
.btn-delete   { color: #6b7280; }
.btn-delete:hover:not(:disabled) { color: #ef4444; background: rgba(239,68,68,.1); }
.btn-delete:disabled { opacity: 0.4; cursor: not-allowed; }

/* Form */
.add-key-form { border-top: 1px solid rgba(255,255,255,.07); padding-top: 1.25rem; }
.form-title   { font-size: 0.8125rem; color: #6b7280; margin: 0 0 0.75rem; }
.form-row     { margin-bottom: 0.625rem; }
.select-key, .input-value {
  width: 100%; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12);
  border-radius: 0.5rem; color: #e5e7eb; padding: 0.5rem 0.75rem; font-size: 0.875rem;
  box-sizing: border-box; outline: none;
}
.select-key:focus, .input-value:focus { border-color: #14b8a6; }
.select-key option { background: #1f2937; }
.form-error { font-size: 0.75rem; color: #f87171; margin: 0.25rem 0; }
.btn-save {
  width: 100%; background: #14b8a6; color: #fff; border: none; border-radius: 0.5rem;
  padding: 0.6rem; font-size: 0.875rem; font-weight: 500; cursor: pointer; margin-top: 0.25rem;
}
.btn-save:hover:not(:disabled) { background: #0d9488; }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }

/* States */
.state-placeholder { color: #6b7280; padding: 2rem; text-align: center; }
.state-error       { color: #f87171; padding: 2rem; text-align: center; }
.empty-hint        { font-size: 0.8125rem; color: #4b5563; }

/* Toast */
.toast {
  position: fixed; bottom: 1.5rem; right: 1.5rem;
  padding: 0.75rem 1.25rem; border-radius: 0.5rem; font-size: 0.875rem;
  box-shadow: 0 4px 20px rgba(0,0,0,.4);
}
.toast-success { background: #064e3b; color: #6ee7b7; border: 1px solid #065f46; }
.toast-error   { background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; }
.toast-enter-active, .toast-leave-active { transition: opacity 0.3s; }
.toast-enter-from, .toast-leave-to      { opacity: 0; }
</style>
