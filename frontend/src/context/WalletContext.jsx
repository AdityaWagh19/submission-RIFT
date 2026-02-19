import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { PeraWalletConnect } from '@perawallet/connect';

const WalletContext = createContext(null);

const peraWallet = new PeraWalletConnect({ chainId: 416002 }); // TestNet

export function WalletProvider({ children }) {
    const [accounts, setAccounts] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const reconnectRef = useRef(false);

    useEffect(() => {
        // Try reconnect on mount
        peraWallet.reconnectSession()
            .then((accts) => {
                if (accts.length) {
                    setAccounts(accts);
                    setIsConnected(true);
                    peraWallet.connector?.on('disconnect', handleDisconnect);
                }
            })
            .catch(() => { });
    }, []);

    const handleDisconnect = useCallback(() => {
        setAccounts([]);
        setIsConnected(false);
    }, []);

    const connect = useCallback(async () => {
        try {
            const accts = await peraWallet.connect();
            setAccounts(accts);
            setIsConnected(true);
            peraWallet.connector?.on('disconnect', handleDisconnect);
            return accts;
        } catch (err) {
            if (err?.data?.type !== 'CONNECT_MODAL_CLOSED') {
                console.error('Pera connect error:', err);
            }
            throw err;
        }
    }, [handleDisconnect]);

    const disconnect = useCallback(() => {
        peraWallet.disconnect();
        handleDisconnect();
    }, [handleDisconnect]);

    const signBytes = useCallback(async (bytes) => {
        if (!accounts.length) throw new Error('No wallet connected');
        const result = await peraWallet.signData(
            [{ data: bytes, message: 'FanForge Authentication' }],
            accounts[0],
        );
        return result[0];
    }, [accounts]);

    const signTxn = useCallback(async (txnObjects) => {
        if (!accounts.length) throw new Error('No wallet connected');
        // Pera SDK expects: [[{txn: TransactionObject}, {txn: TransactionObject}]]
        // It handles encoding internally via algosdk.encodeUnsignedTransaction
        const txnGroup = Array.isArray(txnObjects)
            ? [txnObjects.map((t) => ({ txn: t.txn || t }))]
            : [[{ txn: txnObjects }]];
        const result = await peraWallet.signTransaction(txnGroup);
        return result;
    }, [accounts]);

    return (
        <WalletContext.Provider value={{
            peraWallet, accounts, isConnected,
            connect, disconnect, signBytes, signTxn,
            address: accounts[0] || null,
        }}>
            {children}
        </WalletContext.Provider>
    );
}

export function useWallet() {
    const ctx = useContext(WalletContext);
    if (!ctx) throw new Error('useWallet must be used within WalletProvider');
    return ctx;
}
