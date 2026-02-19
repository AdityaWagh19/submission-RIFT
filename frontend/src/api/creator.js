import { api } from './client';

export const creatorApi = {
    register: (wallet_address, min_tip_algo = 0.5) =>
        api.post('/creator/register', { wallet_address, min_tip_algo }),

    getDashboard: (wallet) =>
        api.get(`/creator/${wallet}/dashboard`),

    getContract: (wallet) =>
        api.get(`/creator/${wallet}/contract`),

    getContractStats: (wallet) =>
        api.get(`/creator/${wallet}/contract/stats`),

    upgradeContract: (wallet) =>
        api.post(`/creator/${wallet}/upgrade-contract`),

    pauseContract: (wallet) =>
        api.post(`/creator/${wallet}/pause-contract`),

    unpauseContract: (wallet) =>
        api.post(`/creator/${wallet}/unpause-contract`),

    getTemplates: (wallet) =>
        api.get(`/creator/${wallet}/templates`),

    createTemplate: (wallet, formData) =>
        api.upload(`/creator/${wallet}/sticker-template`, formData),

    deleteTemplate: (wallet, templateId) =>
        api.delete(`/creator/${wallet}/template/${templateId}`),

    getProducts: (wallet) =>
        api.get(`/creator/${wallet}/products`),

    createProduct: (wallet, data) =>
        api.post(`/creator/${wallet}/products`, data),

    updateProduct: (wallet, productId, data) =>
        api.patch(`/creator/${wallet}/products/${productId}`, data),

    deleteProduct: (wallet, productId) =>
        api.delete(`/creator/${wallet}/products/${productId}`),

    getDiscounts: (wallet) =>
        api.get(`/creator/${wallet}/discounts`),

    createDiscount: (wallet, data) =>
        api.post(`/creator/${wallet}/discounts`, data),
};
