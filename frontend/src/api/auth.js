import { api } from './client';

export const authApi = {
    createChallenge: (walletAddress) =>
        api.post('/auth/challenge', { walletAddress }, { auth: false }),

    verifySignature: (walletAddress, nonce, signature) =>
        api.post('/auth/verify', { walletAddress, nonce, signature }, { auth: false }),
};
