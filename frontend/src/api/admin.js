import apiClient from './client'

export const adminAPI = {
  async getStats() {
    const response = await apiClient.get('/api/admin/stats')
    return response.data
  },

  // ── Maps ──────────────────────────────────
  async getMaps(params = {}) {
    const response = await apiClient.get('/api/admin/maps', { params })
    return response.data  // { total, maps }
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
    return response.data  // { total, strategies }
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
  async getPromoCodes(params = {}) {
    const response = await apiClient.get('/api/admin/promo-codes', { params })
    return response.data  // { total, promo_codes }
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
  async grantSubscription(id, months) {
    const response = await apiClient.patch(`/api/admin/users/${id}/subscription`, { months })
    return response.data
  },
  async setUserBanned(id, isBanned) {
    const response = await apiClient.patch(`/api/admin/users/${id}/ban`, { is_banned: isBanned })
    return response.data
  },
  async setUserTradeBanned(id, isTradeBanned) {
    const response = await apiClient.patch(`/api/admin/users/${id}/trade-ban`, { is_trade_banned: isTradeBanned })
    return response.data
  },
  async setUserNickname(id, nickname) {
    const response = await apiClient.patch(`/api/admin/users/${id}/nickname`, { nickname })
    return response.data
  },
  async clearUserAvatar(id) {
    const response = await apiClient.delete(`/api/admin/users/${id}/avatar`)
    return response.data
  },
  async setUserPremium(id, unit, amount = null) {
    const response = await apiClient.patch(`/api/admin/users/${id}/premium`, { unit, amount })
    return response.data
  },

  // ── Transactions ──────────────────────────
  async getTransactions(params = {}) {
    const response = await apiClient.get('/api/admin/transactions', { params })
    return response.data
  },
}
