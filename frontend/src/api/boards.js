import apiClient from './client'

export const boardsAPI = {
  async list(params = {}) {
    const response = await apiClient.get('/api/boards', { params })
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
}
