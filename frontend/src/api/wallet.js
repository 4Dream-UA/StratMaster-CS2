import apiClient from './client'

export const walletAPI = {
  async transfer(receiverWalletId, amount) {
    const response = await apiClient.post('/api/wallet/transfer', {
      receiver_wallet_id: receiverWalletId,
      amount,
    })
    return response.data
  },

  async giftSubscription(receiverWalletId, plan, months = null) {
    const response = await apiClient.post('/api/wallet/gift-subscription', {
      receiver_wallet_id: receiverWalletId,
      plan,
      months,
    })
    return response.data
  },

  async listBlocked() {
    const response = await apiClient.get('/api/wallet/blocked')
    return response.data
  },
  async block(walletId) {
    await apiClient.post('/api/wallet/block', { wallet_id: walletId })
  },
  async unblock(walletId) {
    await apiClient.delete(`/api/wallet/block/${walletId}`)
  },
}
