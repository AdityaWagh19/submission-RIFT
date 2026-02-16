/**
 * Contract module — smart contract deployment, funding, and transfer.
 *
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║  SWAP POINT: Replace this file for different contract flows.   ║
 * ║  The wallet, transaction, and UI modules stay unchanged.       ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */
import { CONFIG } from './config.js';
import * as wallet from './wallet.js';
import * as tx from './transaction.js';

const STORAGE_KEY_APP_ID = 'algorand_contract_app_id';
const STORAGE_KEY_APP_ADDR = 'algorand_contract_app_address';

let appId = null;
let appAddress = null;

// ── Getters ────────────────────────────────────────────────────────

export function getAppId() { return appId; }
export function getAppAddress() { return appAddress; }
export function isDeployed() { return appId !== null; }

// ── Persistence ────────────────────────────────────────────────────

export function loadSaved() {
    const savedId = localStorage.getItem(STORAGE_KEY_APP_ID);
    const savedAddr = localStorage.getItem(STORAGE_KEY_APP_ADDR);
    if (savedId) {
        appId = parseInt(savedId, 10);
        appAddress = savedAddr;
        console.log(`■ Loaded saved contract: ${appId}`);
        return true;
    }
    return false;
}

function save(id, address) {
    appId = id;
    appAddress = address;
    localStorage.setItem(STORAGE_KEY_APP_ID, id.toString());
    localStorage.setItem(STORAGE_KEY_APP_ADDR, address);
}

// ── Deploy ─────────────────────────────────────────────────────────

/**
 * Deploy the smart contract to TestNet.
 * @param {Function} onStatus - Status callback: (message) => void
 * @returns {{ appId: number, appAddress: string }}
 */
export async function deploy(onStatus) {
    const sender = wallet.getAccount();
    if (!sender) throw new Error('Wallet not connected');

    onStatus('Creating deployment transaction...');

    const resp = await fetch(`${CONFIG.BACKEND_URL}/contract/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sender,
            contractName: CONFIG.DEFAULT_CONTRACT,
        }),
    });
    if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Deploy transaction creation failed');
    }

    const data = await resp.json();

    // Decode and sign
    onStatus('Waiting for wallet signature...');
    const txnBytes = tx.base64ToUint8Array(data.unsignedTxn);
    const txn = algosdk.decodeUnsignedTransaction(txnBytes);
    const signed = await wallet.signTransaction(txn);

    // Submit
    onStatus('Deploying contract to TestNet...');
    const txId = await tx.submitSingle(signed);
    console.log('■ Deployment transaction signed. TX:', txId);

    // Poll for app ID
    onStatus('Confirming deployment...');
    const newAppId = await _pollForAppId(txId);

    if (!newAppId) throw new Error('Could not retrieve App ID from deployment');

    const newAppAddress = algosdk.getApplicationAddress(newAppId);
    save(newAppId, newAppAddress);

    console.log(`✅ Contract deployed! App ID: ${newAppId}, Address: ${newAppAddress}`);
    return { appId: newAppId, appAddress: newAppAddress };
}

async function _pollForAppId(txId, retries = 10) {
    for (let i = 0; i < retries; i++) {
        await new Promise(r => setTimeout(r, 2000));
        try {
            const resp = await fetch(
                `https://testnet-idx.algonode.cloud/v2/transactions/${txId}`
            );
            if (resp.ok) {
                const data = await resp.json();
                const createdId = data.transaction?.['created-application-index'];
                if (createdId) return createdId;
            }
        } catch (e) {
            console.log(`Poll attempt ${i + 1}/${retries}...`);
        }
    }
    return null;
}

// ── Fund ───────────────────────────────────────────────────────────

/**
 * Fund the deployed contract with ALGO for min balance + inner txn fees.
 * @param {Function} onStatus - Status callback
 * @returns {string} Transaction ID
 */
export async function fund(onStatus) {
    if (!appId) throw new Error('No contract deployed');
    const sender = wallet.getAccount();

    onStatus('Creating fund transaction...');

    const resp = await fetch(`${CONFIG.BACKEND_URL}/contract/fund`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sender,
            appId,
            amount: CONFIG.CONTRACT_FUND_AMOUNT,
        }),
    });
    if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Fund transaction creation failed');
    }

    const data = await resp.json();

    onStatus('Waiting for wallet signature...');
    const txnBytes = tx.base64ToUint8Array(data.unsignedTxn);
    const txn = algosdk.decodeUnsignedTransaction(txnBytes);
    const signed = await wallet.signTransaction(txn);

    onStatus('Submitting fund transaction...');
    const txId = await tx.submitSingle(signed);
    console.log('✅ Contract funded! TX:', txId);
    return txId;
}

// ── Transfer ───────────────────────────────────────────────────────

/**
 * Execute a payment transfer through the smart contract.
 * Builds the atomic group (Payment + AppCall) entirely on the frontend.
 *
 * @param {string} receiver - Receiver address
 * @param {number} amountMicroAlgos - Amount in microAlgos
 * @param {Function} onStatus - Status callback
 * @returns {string} Transaction ID
 */
export async function transfer(receiver, amountMicroAlgos, onStatus) {
    if (!appId) throw new Error('No contract deployed');
    const sender = wallet.getAccount();

    onStatus('Fetching transaction params...');
    const suggestedParams = await tx.getSuggestedParams();

    onStatus('Building contract transfer...');
    const contractAddress = algosdk.getApplicationAddress(appId);
    const receiverBytes = algosdk.decodeAddress(receiver).publicKey;

    // Transaction 0: Payment from user → contract
    const paymentTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
        sender,
        receiver: contractAddress,
        amount: amountMicroAlgos,
        suggestedParams,
    });

    // Transaction 1: App call with higher fee (covers inner txn)
    const appParams = { ...suggestedParams, fee: Math.max(suggestedParams.fee, 2000) };
    const appCallTxn = algosdk.makeApplicationCallTxnFromObject({
        sender,
        appIndex: appId,
        onComplete: algosdk.OnApplicationComplete.NoOpOC,
        appArgs: [
            new Uint8Array(Buffer.from('transfer')),
            receiverBytes,
        ],
        accounts: [receiver],
        suggestedParams: appParams,
    });

    // Assign group ID
    const group = algosdk.assignGroupID([paymentTxn, appCallTxn]);

    // Sign with Pera Wallet
    onStatus('Waiting for wallet signature...');
    const signedTxns = await wallet.signGroup(group);
    console.log(`✅ Atomic group signed (${signedTxns.length} txns)`);

    // Submit
    onStatus('Submitting to Algorand TestNet...');
    const txId = await tx.submitGroup(signedTxns);
    console.log('✅ Contract transfer successful! TX:', txId);
    return txId;
}
