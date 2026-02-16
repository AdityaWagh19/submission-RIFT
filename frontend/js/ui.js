/**
 * UI module — DOM manipulation, notifications, and visual state management.
 */
import { CONFIG } from './config.js';

// ── DOM Elements ───────────────────────────────────────────────────

export const el = {
    // Wallet
    walletDisconnected: document.getElementById('walletDisconnected'),
    walletConnected: document.getElementById('walletConnected'),
    connectBtn: document.getElementById('connectBtn'),
    disconnectBtn: document.getElementById('disconnectBtn'),
    walletAddressDisplay: document.getElementById('walletAddressDisplay'),

    // Contract
    contractSection: document.getElementById('contractSection'),
    contractStatus: document.getElementById('contractStatus'),
    contractInfo: document.getElementById('contractInfo'),
    contractAppId: document.getElementById('contractAppId'),
    contractAppAddress: document.getElementById('contractAppAddress'),
    deployBtn: document.getElementById('deployBtn'),
    fundBtn: document.getElementById('fundBtn'),
    fundStatus: document.getElementById('fundStatus'),
    deployStatus: document.getElementById('deployStatus'),

    // Transfer form
    transferSection: document.getElementById('transferSection'),
    transferForm: document.getElementById('transferForm'),
    receiverAddress: document.getElementById('receiverAddress'),
    amount: document.getElementById('amount'),
    sendBtn: document.getElementById('sendBtn'),
    sendBtnText: document.getElementById('sendBtnText'),
    sendBtnSpinner: document.getElementById('sendBtnSpinner'),

    // Errors
    addressError: document.getElementById('addressError'),
    amountError: document.getElementById('amountError'),

    // Loading & Results
    loadingState: document.getElementById('loadingState'),
    loadingMessage: document.getElementById('loadingMessage'),
    successState: document.getElementById('successState'),
    errorState: document.getElementById('errorState'),
    errorMessage: document.getElementById('errorMessage'),
    txDetails: document.getElementById('txDetails'),
    txId: document.getElementById('txId'),
    txLink: document.getElementById('txLink'),
    newTxBtn: document.getElementById('newTxBtn'),
    retryBtn: document.getElementById('retryBtn'),
};

// ── Wallet UI ──────────────────────────────────────────────────────

export function showWalletConnected(address) {
    el.walletDisconnected.style.display = 'none';
    el.walletConnected.style.display = 'flex';
    el.walletAddressDisplay.textContent = truncateAddress(address);

    if (el.contractSection) el.contractSection.style.display = 'block';
    if (el.transferSection) el.transferSection.style.display = 'block';
}

export function showWalletDisconnected() {
    el.walletDisconnected.style.display = 'flex';
    el.walletConnected.style.display = 'none';
    el.walletAddressDisplay.textContent = '';

    if (el.contractSection) el.contractSection.style.display = 'none';
    if (el.transferSection) el.transferSection.style.display = 'none';
}

// ── Contract UI ────────────────────────────────────────────────────

export function showContractDeployed(appId, appAddress) {
    if (el.contractInfo) el.contractInfo.style.display = 'block';
    if (el.contractAppId) el.contractAppId.textContent = appId;
    if (el.contractAppAddress) el.contractAppAddress.textContent = truncateAddress(appAddress);
    if (el.contractStatus) {
        el.contractStatus.textContent = '✅ Contract Active';
        el.contractStatus.style.color = '#86efac';
    }
}

export function showContractStatus(msg) {
    if (el.deployStatus) {
        el.deployStatus.textContent = msg;
        el.deployStatus.style.display = 'block';
    }
}

export function hideContractStatus() {
    if (el.deployStatus) el.deployStatus.style.display = 'none';
}

// ── Form Validation ────────────────────────────────────────────────

export function validateForm() {
    let valid = true;

    const address = el.receiverAddress?.value?.trim();
    if (!address || address.length !== 58) {
        showFieldError(el.addressError, 'Enter a valid 58-character Algorand address');
        valid = false;
    } else {
        hideFieldError(el.addressError);
    }

    const amt = parseFloat(el.amount?.value);
    if (!amt || amt < CONFIG.MIN_TRANSACTION_AMOUNT) {
        showFieldError(el.amountError, `Minimum amount is ${CONFIG.MIN_TRANSACTION_AMOUNT} ALGO`);
        valid = false;
    } else {
        hideFieldError(el.amountError);
    }

    return valid;
}

function showFieldError(element, message) {
    if (element) { element.textContent = message; element.style.display = 'block'; }
}

function hideFieldError(element) {
    if (element) { element.textContent = ''; element.style.display = 'none'; }
}

// ── Loading / Results ──────────────────────────────────────────────

export function showLoading(message) {
    if (el.loadingState) { el.loadingState.style.display = 'block'; }
    if (el.loadingMessage) { el.loadingMessage.textContent = message; }
    if (el.successState) el.successState.style.display = 'none';
    if (el.errorState) el.errorState.style.display = 'none';
}

export function hideLoading() {
    if (el.loadingState) el.loadingState.style.display = 'none';
}

export function showSuccess(txId) {
    hideLoading();
    if (el.successState) el.successState.style.display = 'block';
    if (el.errorState) el.errorState.style.display = 'none';
    if (el.txId) el.txId.textContent = txId;
    if (el.txLink) {
        el.txLink.href = `${CONFIG.EXPLORER_URL}/tx/${txId}`;
    }
}

export function showError(message) {
    hideLoading();
    if (el.errorState) el.errorState.style.display = 'block';
    if (el.successState) el.successState.style.display = 'none';
    if (el.errorMessage) el.errorMessage.textContent = message;
}

export function resetForm() {
    if (el.receiverAddress) el.receiverAddress.value = '';
    if (el.amount) el.amount.value = '';
    if (el.successState) el.successState.style.display = 'none';
    if (el.errorState) el.errorState.style.display = 'none';
}

export function setFormEnabled(enabled) {
    if (el.sendBtn) el.sendBtn.disabled = !enabled;
    if (el.receiverAddress) el.receiverAddress.disabled = !enabled;
    if (el.amount) el.amount.disabled = !enabled;
}

// ── Notifications ──────────────────────────────────────────────────

export function showNotification(message, type = 'info') {
    // Simple notification via an existing element or console
    const colors = { info: '#93c5fd', success: '#86efac', error: '#fca5a5', warning: '#fde68a' };
    console.log(`[${type.toUpperCase()}] ${message}`);

    // If there's a notification container in the DOM
    const container = document.getElementById('notification');
    if (container) {
        container.textContent = message;
        container.style.color = colors[type] || colors.info;
        container.style.display = 'block';
        setTimeout(() => { container.style.display = 'none'; }, 5000);
    }
}

// ── Utility ────────────────────────────────────────────────────────

function truncateAddress(addr) {
    if (!addr || addr.length < 12) return addr || '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}
