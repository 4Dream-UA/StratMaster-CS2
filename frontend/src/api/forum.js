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
  async addPost(id, body, replyToPostId = null, visibleToUserIds = null) {
    const response = await apiClient.post(`/api/forum/threads/${id}/posts`, {
      body, reply_to_post_id: replyToPostId, visible_to_user_ids: visibleToUserIds,
    })
    return response.data
  },
  async updatePost(id, body) {
    const response = await apiClient.patch(`/api/forum/posts/${id}`, { body })
    return response.data
  },
  async deletePost(id) {
    const response = await apiClient.delete(`/api/forum/posts/${id}`)
    return response.data
  },
  async restorePost(id) {
    const response = await apiClient.post(`/api/forum/posts/${id}/restore`)
    return response.data
  },
  async permanentlyDeletePost(id) {
    await apiClient.delete(`/api/forum/posts/${id}/permanent`)
  },
  async getPostEdits(id) {
    const response = await apiClient.get(`/api/forum/posts/${id}/edits`)
    return response.data
  },
  async getPostReactors(id, emoji, { limit = 20, offset = 0 } = {}) {
    const response = await apiClient.get(`/api/forum/posts/${id}/reactions`, { params: { emoji, limit, offset } })
    return response.data  // { total, reactors }
  },
  async reportPost(id, reason) {
    await apiClient.post(`/api/forum/posts/${id}/report`, { reason })
  },
  async getPostReports(id) {
    const response = await apiClient.get(`/api/forum/posts/${id}/reports`)
    return response.data
  },
  async dismissPostReports(id) {
    await apiClient.post(`/api/forum/posts/${id}/reports/dismiss`)
  },
  async reportThread(id, reason) {
    await apiClient.post(`/api/forum/threads/${id}/report`, { reason })
  },
  async getThreadReports(id) {
    const response = await apiClient.get(`/api/forum/threads/${id}/reports`)
    return response.data
  },
  async dismissThreadReports(id) {
    await apiClient.post(`/api/forum/threads/${id}/reports/dismiss`)
  },
  async react(postId, emoji) {
    const response = await apiClient.post(`/api/forum/posts/${postId}/react`, { emoji })
    return response.data  // full thread, same shape as getThread
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
