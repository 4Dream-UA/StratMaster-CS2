import apiClient from './client'

export const forumAPI = {
  async listCategories() {
    const response = await apiClient.get('/api/forum/categories')
    return response.data
  },
  async listThreads(key, params = {}) {
    const response = await apiClient.get(`/api/forum/categories/${key}/threads`, { params })
    return response.data  // { total, threads }
  },
  async createThread(key, title, body) {
    const response = await apiClient.post(`/api/forum/categories/${key}/threads`, { title, body })
    return response.data
  },
  async getThread(id) {
    const response = await apiClient.get(`/api/forum/threads/${id}`)
    return response.data
  },
  async addPost(id, body) {
    const response = await apiClient.post(`/api/forum/threads/${id}/posts`, { body })
    return response.data
  },
}
