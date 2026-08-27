import apiClient from './client'

export const boardsAPI = {
  async list(params = {}) {
    const response = await apiClient.get('/api/boards', { params })
    return response.data  // { total, boards }
  },
  async listSharedWithMe(params = {}) {
    const response = await apiClient.get('/api/boards/shared-with-me', { params })
    return response.data  // { total, boards }
  },
  async get(id) {
    const response = await apiClient.get(`/api/boards/${id}`)
    return response.data
  },
  async create(payload) {
    const response = await apiClient.post('/api/boards', payload)
    return response.data
  },
  async update(id, payload) {
    const response = await apiClient.patch(`/api/boards/${id}`, payload)
    return response.data
  },
  async remove(id) {
    await apiClient.delete(`/api/boards/${id}`)
  },

  // ── Sharing ────────────────────────────────
  async createShareLink(id) {
    const response = await apiClient.post(`/api/boards/${id}/share`)
    return response.data  // { share_token }
  },
  async revokeShareLink(id) {
    await apiClient.delete(`/api/boards/${id}/share`)
  },
  async getShared(token) {
    // No X-Init-Data needed — the interceptor still attaches it if present,
    // but the endpoint itself is public.
    const response = await apiClient.get(`/api/boards/shared/${token}`)
    return response.data
  },
  async listCollaborators(id) {
    const response = await apiClient.get(`/api/boards/${id}/collaborators`)
    return response.data
  },
  async addCollaborator(id, walletId) {
    const response = await apiClient.post(`/api/boards/${id}/collaborators`, { wallet_id: walletId })
    return response.data
  },
  async removeCollaborator(id, userId) {
    const response = await apiClient.delete(`/api/boards/${id}/collaborators/${userId}`)
    return response.data
  },
}
