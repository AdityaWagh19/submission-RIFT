import { api } from './client';

export const systemApi = {
    getHealth: () =>
        api.get('/health', { auth: false }),

    getParams: () =>
        api.get('/params', { auth: false }),

    getOnrampConfig: () =>
        api.get('/onramp/config', { auth: false }),

    fundWallet: (walletAddress, amountAlgo = 5.0) =>
        api.post('/simulate/fund-wallet', { walletAddress, amountAlgo }, { auth: false }),

    createOnrampOrder: (fanWallet, creatorWallet, fiatAmount, fiatCurrency = 'INR') =>
        api.post('/onramp/create-order', { fanWallet, creatorWallet, fiatAmount, fiatCurrency }),

    getOnrampOrderStatus: (partnerOrderId) =>
        api.get(`/onramp/order/${partnerOrderId}`),

    getFanOnrampOrders: (wallet) =>
        api.get(`/onramp/fan/${wallet}/orders`),

    submitTxn: (signed_txn, idempotencyKey = null) =>
        api.post('/submit', { signed_txn }, {
            ...(idempotencyKey && { headers: { 'X-Idempotency-Key': idempotencyKey } }),
        }),

    submitGroup: (signed_txns, idempotencyKey = null) =>
        api.post('/submit-group', { signed_txns }, {
            ...(idempotencyKey && { headers: { 'X-Idempotency-Key': idempotencyKey } }),
        }),

    getContractInfo: (name = 'tip_proxy') =>
        api.get('/contract/info', { params: { name }, auth: false }),

    listContracts: () =>
        api.get('/contract/list', { auth: false }),

    deployContract: (sender, contract_name = 'tip_proxy') =>
        api.post('/contract/deploy', { sender, contract_name }),

    fundContract: (sender, app_id, amount) =>
        api.post('/contract/fund', { sender, app_id, amount }),
};
