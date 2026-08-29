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
  async updateThread(id, title) {
    const response = await apiClient.patch(`/api/forum/threads/${id}`, { title })
    return response.data
  },
  async pinThread(id, isPinned) {
    const response = await apiClient.patch(`/api/forum/threads/${id}/pin`, { is_pinned: isPinned })
    return response.data
  },
  async closeThread(id, isClosed) {
    const response = await apiClient.patch(`/api/forum/threads/${id}/close`, { is_closed: isClosed })
    return response.data
  },
  async toggleWatch(id) {
    const response = await apiClient.post(`/api/forum/threads/${id}/watch`)
    return response.data  // { is_watching }
  },
  async deleteThread(id) {
    await apiClient.delete(`/api/forum/threads/${id}`)
  },
  async addPost(id, body, replyToPostId = null) {
    const response = await apiClient.post(`/api/forum/threads/${id}/posts`, { body, reply_to_post_id: replyToPostId })
    return response.data
  },
  async updatePost(id, body) {
    const response = await apiClient.patch(`/api/forum/posts/${id}`, { body })
    return response.data
  },
  async uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/api/forum/uploads', formData, {
      headers: { 'Content-Type': undefined },
    })
    return response.data  // { url }
  },
  async createShareLink(id) {
    const response = await apiClient.post(`/api/forum/threads/${id}/share`)
    return response.data  // { share_token }
  },
  async revokeShareLink(id) {
    await apiClient.delete(`/api/forum/threads/${id}/share`)
  },
  async getShared(token) {
    const response = await apiClient.get(`/api/forum/shared/${token}`)
    return response.data
  },
  async updateCategory(key, name, description) {
    const response = await apiClient.patch(`/api/forum/categories/${key}`, { name, description })
    return response.data
  },
}
