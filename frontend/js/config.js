/**
 * Configuration — externalized settings for the dApp.
 * Change these when switching networks or backends.
 */
export const CONFIG = {
    // Backend API
    BACKEND_URL: 'http://localhost:8000',

    // Algorand network
    NETWORK: 'testnet',
    EXPLORER_URL: 'https://testnet.algoexplorer.io',

    // Transaction defaults
    MIN_TRANSACTION_AMOUNT: 0.001,
    PARAMS_CACHE_TTL: 30000, // 30 seconds

    // Contract defaults
    CONTRACT_FUND_AMOUNT: 200000, // 0.2 ALGO in microAlgos
    DEFAULT_CONTRACT: 'payment_proxy',
};
