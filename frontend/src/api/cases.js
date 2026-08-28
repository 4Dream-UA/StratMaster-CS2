import apiClient from './client'

export const casesAPI = {
  async list() {
    const response = await apiClient.get('/api/cases')
    return response.data
  },
  async open(caseId) {
    const response = await apiClient.post(`/api/cases/${caseId}/open`)
    return response.data
  },
  async history() {
    const response = await apiClient.get('/api/cases/openings/history')
    return response.data.openings
  },
}
