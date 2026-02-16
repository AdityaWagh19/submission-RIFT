// Polyfills for Node.js globals in the browser
if (typeof global === 'undefined') {
    window.global = window;
}
if (typeof process === 'undefined') {
    window.process = { env: {}, version: '', browser: true };
}
if (typeof Buffer === 'undefined') {
    window.Buffer = { isBuffer: () => false, from: () => ({}) };
}

// Bundle entry point - exports libraries to the global scope
import algosdk from 'algosdk';
import { PeraWalletConnect } from '@perawallet/connect';

window.algosdk = algosdk;
window.PeraWalletConnect = PeraWalletConnect;

console.log('✅ algosdk loaded');
console.log('✅ PeraWalletConnect loaded');
