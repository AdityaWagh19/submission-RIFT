import { api } from './client';

export const fanApi = {
    getInventory: (wallet, skip = 0, limit = 50) =>
        api.get(`/fan/${wallet}/inventory`, { params: { skip, limit } }),

    getPending: (wallet) =>
        api.get(`/fan/${wallet}/pending`),

    claimNFT: (wallet, nftId) =>
        api.post(`/fan/${wallet}/claim/${nftId}`),

    getStats: (wallet) =>
        api.get(`/fan/${wallet}/stats`),

    getGoldenOdds: (wallet, amount_algo = 1.0) =>
        api.get(`/fan/${wallet}/golden-odds`, { params: { amount_algo } }),
};
