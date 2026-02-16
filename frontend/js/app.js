/**
 * Algorand Fintech Boilerplate — Main Application Entry
 *
 * This is the orchestrator that wires together:
 *   - wallet.js  → Pera Wallet connection
 *   - contract.js → Smart contract lifecycle (SWAP POINT)
 *   - transaction.js → Transaction building & submission
 *   - ui.js → DOM state management
 */
import { CONFIG } from './config.js';
import * as wallet from './wallet.js';
import * as contract from './contract.js';
import * as ui from './ui.js';

// ── Initialization ─────────────────────────────────────────────────

async function init() {
    console.log('=== Initializing Algorand Fintech Boilerplate ===');

    // Set up wallet callbacks
    wallet.setCallbacks(onWalletConnected, onWalletDisconnected);

    // Initialize wallet
    await wallet.init();

    // Load saved contract state
    if (contract.loadSaved()) {
        ui.showContractDeployed(contract.getAppId(), contract.getAppAddress());
    }

    // Wire events
    setupEventListeners();

    console.log('=== App initialized successfully ===');
}

// ── Event Listeners ────────────────────────────────────────────────

function setupEventListeners() {
    ui.el.connectBtn?.addEventListener('click', () => wallet.connect());
    ui.el.disconnectBtn?.addEventListener('click', () => wallet.disconnect());
    ui.el.deployBtn?.addEventListener('click', handleDeploy);
    ui.el.fundBtn?.addEventListener('click', handleFund);
    ui.el.transferForm?.addEventListener('submit', handleTransfer);
    ui.el.newTxBtn?.addEventListener('click', ui.resetForm);
    ui.el.retryBtn?.addEventListener('click', (e) => handleTransfer(e));
    console.log('■ Event listeners set up');
}

// ── Wallet Callbacks ───────────────────────────────────────────────

function onWalletConnected(account) {
    ui.showWalletConnected(account);
}

function onWalletDisconnected() {
    ui.showWalletDisconnected();
}

// ── Contract Handlers ──────────────────────────────────────────────

async function handleDeploy() {
    ui.el.deployBtn.disabled = true;
    try {
        const result = await contract.deploy((msg) => ui.showContractStatus(msg));
        ui.showContractDeployed(result.appId, result.appAddress);
        ui.hideContractStatus();
        ui.showNotification('Contract deployed successfully!', 'success');
    } catch (error) {
        console.error('Deploy error:', error);
        ui.showContractStatus('❌ ' + error.message);
        ui.showNotification(error.message, 'error');
    } finally {
        ui.el.deployBtn.disabled = false;
    }
}

async function handleFund() {
    ui.el.fundBtn.disabled = true;
    try {
        const txId = await contract.fund((msg) => {
            if (ui.el.fundStatus) {
                ui.el.fundStatus.textContent = msg;
                ui.el.fundStatus.style.color = '#93c5fd';
            }
        });
        if (ui.el.fundStatus) {
            ui.el.fundStatus.textContent = `✅ Funded! TX: ${txId.slice(0, 12)}...`;
            ui.el.fundStatus.style.color = '#86efac';
        }
    } catch (error) {
        console.error('Fund error:', error);
        if (ui.el.fundStatus) {
            ui.el.fundStatus.textContent = '❌ ' + error.message;
            ui.el.fundStatus.style.color = '#fca5a5';
        }
    } finally {
        ui.el.fundBtn.disabled = false;
    }
}

async function handleTransfer(event) {
    if (event && event.preventDefault) event.preventDefault();

    if (!ui.validateForm()) return;
    if (!contract.isDeployed()) {
        ui.showNotification('Please deploy and fund the contract first.', 'error');
        return;
    }

    const receiver = ui.el.receiverAddress.value.trim();
    const amountAlgo = parseFloat(ui.el.amount.value);
    const amountMicroAlgos = Math.floor(amountAlgo * 1_000_000);

    console.log(`=== Transfer: ${amountAlgo} ALGO → ${receiver} ===`);
    ui.setFormEnabled(false);

    try {
        const txId = await contract.transfer(receiver, amountMicroAlgos, (msg) => {
            ui.showLoading(msg);
        });
        ui.showSuccess(txId);
    } catch (error) {
        console.error('Transfer error:', error);
        ui.showError(error.message || 'Transaction failed. Please try again.');
    } finally {
        ui.setFormEnabled(true);
    }
}

// ── Start ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
