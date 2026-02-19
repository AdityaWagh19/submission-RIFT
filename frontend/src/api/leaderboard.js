import { api } from './client';

export const leaderboardApi = {
    getGlobalTopCreators: (limit = 50) =>
        api.get('/leaderboard/global/top-creators', { params: { limit }, auth: false }),

    getCreatorLeaderboard: (creatorWallet, limit = 20) =>
        api.get(`/leaderboard/${creatorWallet}`, { params: { limit }, auth: false }),
};
