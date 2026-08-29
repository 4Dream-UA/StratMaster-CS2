import apiClient from './client'

export const casesAPI = {
  async list() {
    const response = await apiClient.get('/api/cases')
    return response.data
  },
  async inventory() {
    const response = await apiClient.get('/api/cases/inventory')
    return response.data
  },
  async buy(caseId, quantity = 1) {
    const response = await apiClient.post(`/api/cases/${caseId}/buy`, { quantity })
    return response.data
  },
  async openInventory(caseId, quantity) {
    const response = await apiClient.post('/api/cases/inventory/open', { case_id: caseId, quantity })
    return response.data
  },
  async history() {
    const response = await apiClient.get('/api/cases/openings/history')
    return response.data.openings
  },
}
