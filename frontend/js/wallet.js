/**
 * Wallet module — Pera Wallet connection lifecycle.
 */
import { CONFIG } from './config.js';

let peraWallet = null;
let connectedAccount = null;

// Callbacks set by app.js
let _onConnect = null;
let _onDisconnect = null;

export function setCallbacks(onConnect, onDisconnect) {
    _onConnect = onConnect;
    _onDisconnect = onDisconnect;
}

export function getAccount() {
    return connectedAccount;
}

export function isConnected() {
    return connectedAccount !== null;
}

export async function init() {
    peraWallet = new PeraWalletConnect();
    console.log('■ Pera Wallet instance created');

    // Check for existing session
    console.log('Checking for existing session...');
    try {
        const accounts = await peraWallet.reconnectSession();
        if (accounts.length > 0) {
            connectedAccount = accounts[0];
            console.log(`■ Reconnected to existing session: ${connectedAccount}`);
            if (_onConnect) _onConnect(connectedAccount);
        }
    } catch (e) {
        console.log('No existing session found');
    }

    // Handle disconnect events
    peraWallet.connector?.on('disconnect', () => {
        connectedAccount = null;
        if (_onDisconnect) _onDisconnect();
    });
}

export async function connect() {
    console.log('=== connect wallet clicked ===');
    try {
        const accounts = await peraWallet.connect();
        connectedAccount = accounts[0];
        console.log(`■ Wallet connected: ${connectedAccount}`);
        if (_onConnect) _onConnect(connectedAccount);
        return connectedAccount;
    } catch (error) {
        console.error('Wallet connection failed:', error);
        throw error;
    }
}

export async function disconnect() {
    try {
        await peraWallet.disconnect();
        connectedAccount = null;
        console.log('■ Wallet disconnected');
        if (_onDisconnect) _onDisconnect();
    } catch (error) {
        console.error('Disconnect error:', error);
    }
}

/**
 * Sign a single transaction with Pera Wallet.
 * @param {Transaction} txn - algosdk Transaction object
 * @returns {Uint8Array} Signed transaction bytes
 */
export async function signTransaction(txn) {
    const group = [{ txn, signers: [connectedAccount] }];
    const signed = await peraWallet.signTransaction([group]);
    return signed[0];
}

/**
 * Sign an atomic group of transactions with Pera Wallet.
 * @param {Transaction[]} txns - Array of algosdk Transaction objects
 * @returns {Uint8Array[]} Array of signed transaction bytes
 */
export async function signGroup(txns) {
    const group = txns.map(txn => ({ txn, signers: [connectedAccount] }));
    const signed = await peraWallet.signTransaction([group]);
    return signed;
}
