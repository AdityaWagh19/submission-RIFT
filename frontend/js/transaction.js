/**
 * Transaction module — transaction building, encoding, and submission.
 */
import { CONFIG } from './config.js';

/**
 * Fetch suggested transaction params from the backend.
 * @returns {Object} algosdk-compatible suggested params
 */
export async function getSuggestedParams() {
    const resp = await fetch(`${CONFIG.BACKEND_URL}/params`);
    if (!resp.ok) throw new Error('Failed to fetch transaction params');
    const data = await resp.json();

    // Convert genesis hash from base64 string to Uint8Array
    let genesisHashBytes = data.genesisHash;
    if (typeof genesisHashBytes === 'string') {
        const binary = atob(genesisHashBytes);
        genesisHashBytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            genesisHashBytes[i] = binary.charCodeAt(i);
        }
    }

    return {
        fee: Math.max(data.fee, 1000),
        flatFee: true,
        firstValid: data.firstValidRound,
        lastValid: data.lastValidRound,
        genesisID: data.genesisId,
        genesisHash: genesisHashBytes,
    };
}

/**
 * Submit a single signed transaction to the backend.
 * @param {Uint8Array} signedTxn - Signed transaction bytes
 * @returns {string} Transaction ID
 */
export async function submitSingle(signedTxn) {
    const b64 = uint8ArrayToBase64(signedTxn);
    const resp = await fetch(`${CONFIG.BACKEND_URL}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signed_txn: b64 }),
    });
    if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Transaction submission failed');
    }
    const data = await resp.json();
    return data.txId;
}

/**
 * Submit an atomic group of signed transactions.
 * @param {Uint8Array[]} signedTxns - Array of signed transaction bytes
 * @returns {string} First transaction ID
 */
export async function submitGroup(signedTxns) {
    const b64Array = signedTxns.map(uint8ArrayToBase64);
    const resp = await fetch(`${CONFIG.BACKEND_URL}/submit-group`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signed_txns: b64Array }),
    });
    if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Group submission failed');
    }
    const data = await resp.json();
    return data.txId;
}

// ── Encoding Helpers ───────────────────────────────────────────────

export function base64ToUint8Array(b64) {
    const raw = atob(b64);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
        bytes[i] = raw.charCodeAt(i);
    }
    return bytes;
}

export function uint8ArrayToBase64(arr) {
    const byteArray = [];
    for (let i = 0; i < arr.length; i++) {
        byteArray.push(arr[i] & 0xFF);
    }
    let binary = '';
    for (let i = 0; i < byteArray.length; i++) {
        binary += String.fromCharCode(byteArray[i]);
    }
    return btoa(binary);
}
