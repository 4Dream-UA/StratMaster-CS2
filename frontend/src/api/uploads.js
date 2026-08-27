import apiClient from './client'

export const uploadsAPI = {
  async uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/api/admin/uploads', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data  // { url }
  },
}
