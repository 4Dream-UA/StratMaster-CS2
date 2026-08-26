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
}
