import { api } from './client';

export const merchApi = {
    getStoreCatalog: (creatorWallet, limit = 50, offset = 0) =>
        api.get(`/creator/${creatorWallet}/store`, { params: { limit, offset }, auth: false }),

    getMembersOnlyCatalog: (creatorWallet, fanWallet) =>
        api.get(`/creator/${creatorWallet}/store/members-only`, { params: { fanWallet } }),

    getQuote: (creatorWallet, data) =>
        api.post(`/creator/${creatorWallet}/store/quote`, data),

    createOrder: (creatorWallet, data) =>
        api.post(`/creator/${creatorWallet}/store/order`, data),

    getFanOrders: (wallet, limit = 50, offset = 0) =>
        api.get(`/fan/${wallet}/orders`, { params: { limit, offset } }),
};
