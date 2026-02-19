export const API_BASE_URL = 'http://localhost:8000';
export const ALGO_DECIMALS = 6;

export const truncateWallet = (addr) =>
    addr ? `${addr.slice(0, 4)}...${addr.slice(-4)}` : '—';

export const microToAlgo = (micro) =>
    micro ? (micro / 1_000_000).toFixed(2) : '0.00';

export const algoToMicro = (algo) =>
    Math.round(algo * 1_000_000);

export const formatDate = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
};

export const timeAgo = (iso) => {
    if (!iso) return '';
    const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (secs < 60) return `${secs}s ago`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
};
