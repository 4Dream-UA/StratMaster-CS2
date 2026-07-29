import apiClient from './client'

export const adminAPI = {
  async getStats() {
    const response = await apiClient.get('/api/admin/stats')
    return response.data
  },

  // ── Maps ──────────────────────────────────
  async getMaps() {
    const response = await apiClient.get('/api/admin/maps')
    return response.data
  },
  async createMap(payload) {
    const response = await apiClient.post('/api/admin/maps', payload)
    return response.data
  },
  async updateMap(id, payload) {
    const response = await apiClient.patch(`/api/admin/maps/${id}`, payload)
    return response.data
  },

  // ── Strategies ────────────────────────────
  async getBuyTags() {
    const response = await apiClient.get('/api/admin/buy-tags')
    return response.data
  },
  async getStrategies(params = {}) {
    const response = await apiClient.get('/api/admin/strategies', { params })
    return response.data
  },
  async createStrategy(payload) {
    const response = await apiClient.post('/api/admin/strategies', payload)
    return response.data
  },
  async updateStrategy(id, payload) {
    const response = await apiClient.patch(`/api/admin/strategies/${id}`, payload)
    return response.data
  },
  async deleteStrategy(id) {
    await apiClient.delete(`/api/admin/strategies/${id}`)
  },

  // ── Promo codes ───────────────────────────
  async getPromoCodes() {
    const response = await apiClient.get('/api/admin/promo-codes')
    return response.data
  },
  async createPromoCode(payload) {
    const response = await apiClient.post('/api/admin/promo-codes', payload)
    return response.data
  },
  async togglePromoCode(id, isActive) {
    const response = await apiClient.patch(`/api/admin/promo-codes/${id}`, { is_active: isActive })
    return response.data
  },

  // ── Users ─────────────────────────────────
  async getUsers(params = {}) {
    const response = await apiClient.get('/api/admin/users', { params })
    return response.data
  },
  async setUserAdmin(id, isAdmin) {
    const response = await apiClient.patch(`/api/admin/users/${id}/admin`, { is_admin: isAdmin })
    return response.data
  },
}
