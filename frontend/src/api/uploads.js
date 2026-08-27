import apiClient from './client'

export const uploadsAPI = {
  async uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    // apiClient defaults Content-Type to application/json for every request;
    // for FormData that must be unset (not just left off) so the browser
    // generates its own multipart boundary — a manually-set or leaked JSON
    // Content-Type here silently breaks the upload on some WebView engines.
    const response = await apiClient.post('/api/admin/uploads', formData, {
      headers: { 'Content-Type': undefined },
    })
    return response.data  // { url }
  },
}
