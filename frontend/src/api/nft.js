import { api } from './client';

export const nftApi = {
    getInventory: (wallet, skip = 0, limit = 50) =>
        api.get(`/nft/inventory/${wallet}`, { params: { skip, limit } }),

    getDetails: (assetId) =>
        api.get(`/nft/${assetId}`),

    createOptIn: (fan_wallet, asset_id) =>
        api.post('/nft/optin', { fan_wallet, asset_id }),

    transferNFT: (from_wallet, to_wallet, asset_id) =>
        api.post('/nft/transfer', { from_wallet, to_wallet, asset_id }),
};
