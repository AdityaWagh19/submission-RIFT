import { api } from './client';

// ── Butki Loyalty ──
export const butkiApi = {
    getFanLoyalty: (wallet) =>
        api.get(`/butki/${wallet}/loyalty`, { auth: false }),

    getFanLoyaltyForCreator: (wallet, creatorWallet) =>
        api.get(`/butki/${wallet}/loyalty/${creatorWallet}`, { auth: false }),

    getLeaderboard: (creatorWallet, limit = 50) =>
        api.get(`/butki/leaderboard/${creatorWallet}`, { params: { limit }, auth: false }),
};

// ── Bauni Membership ──
export const bauniApi = {
    getMembershipStatus: (wallet, creatorWallet) =>
        api.get(`/bauni/${wallet}/membership/${creatorWallet}`, { auth: false }),

    getAllMemberships: (wallet, active_only = true) =>
        api.get(`/bauni/${wallet}/memberships`, { params: { active_only } }),

    verifyMembership: (fan_wallet, creator_wallet) =>
        api.post('/bauni/verify', { fan_wallet, creator_wallet }),
};

// ── Shawty Collectibles ──
export const shawtyApi = {
    getTokens: (wallet, include_spent = false) =>
        api.get(`/shawty/${wallet}/tokens`, { params: { include_spent } }),

    burnForMerch: (fan_wallet, asset_id, item_description) =>
        api.post('/shawty/burn', { fan_wallet, asset_id, item_description }),

    lockForDiscount: (fan_wallet, asset_id, discount_description) =>
        api.post('/shawty/lock', { fan_wallet, asset_id, discount_description }),

    transfer: (from_wallet, to_wallet, asset_id) =>
        api.post('/shawty/transfer', { from_wallet, to_wallet, asset_id }),

    validateOwnership: (wallet, assetId) =>
        api.get(`/shawty/${wallet}/validate/${assetId}`),

    getRedemptions: (wallet, limit = 50) =>
        api.get(`/shawty/${wallet}/redemptions`, { params: { limit } }),
};
