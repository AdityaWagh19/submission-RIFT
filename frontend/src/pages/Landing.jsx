import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useWallet } from '../context/WalletContext';
import { useToast } from '../context/ToastContext';
import { systemApi } from '../api/system';

export default function Landing() {
    const { wallet, role, isAuthenticated, login } = useAuth();
    const { connect, signBytes, isConnected, address } = useWallet();
    const toast = useToast();
    const navigate = useNavigate();

    const [health, setHealth] = useState(null);
    const [connecting, setConnecting] = useState(false);
    const [funding, setFunding] = useState(false);
    const [fundAmount, setFundAmount] = useState('5');

    // Fetch health on mount
    useEffect(() => {
        systemApi.getHealth()
            .then(setHealth)
            .catch(() => setHealth({ status: 'unhealthy', algorand_connected: false }));
    }, []);

    const handleConnect = async () => {
        setConnecting(true);
        try {
            const accounts = await connect();
            const walletAddr = accounts[0];
            const result = await login(walletAddr, signBytes);
            toast.success(`Connected as ${result.role}!`);
        } catch (err) {
            if (err?.data?.type !== 'CONNECT_MODAL_CLOSED') {
                toast.error(err.message || 'Connection failed');
            }
        } finally {
            setConnecting(false);
        }
    };

    const handleFund = async () => {
        setFunding(true);
        try {
            await systemApi.fundWallet(wallet, parseFloat(fundAmount));
            toast.success(`Funded ${fundAmount} ALGO to your wallet!`);
        } catch (err) {
            toast.error(err.message || 'Funding failed');
        } finally {
            setFunding(false);
        }
    };

    return (
        <div className="page-container">
            {/* ── HERO ── */}
            <section className="hero">
                <h1>FanForge</h1>
                <p className="subtitle">
                    Web3 creator economy on Algorand. Tip creators, earn NFTs, unlock exclusive perks.
                </p>

                <div className="nft-showcase">
                    <div className="nft-showcase-card">
                        <div className="showcase-emoji">🏆</div>
                        <h3>Butki</h3>
                        <p>Loyalty badge — tip 5 times to earn one. Soulbound.</p>
                    </div>
                    <div className="nft-showcase-card">
                        <div className="showcase-emoji">🎫</div>
                        <h3>Bauni</h3>
                        <p>Membership — 30-day pass for exclusive content. Soulbound.</p>
                    </div>
                    <div className="nft-showcase-card">
                        <div className="showcase-emoji">🌟</div>
                        <h3>Shawty</h3>
                        <p>Collectible — trade, burn for merch, lock for discounts.</p>
                    </div>
                </div>
            </section>

            {/* ── CONNECT ── */}
            {!isAuthenticated && (
                <section className="connect-section">
                    <div className="connect-card card-glass">
                        <h2>Get Started</h2>
                        <p>Connect your Pera Wallet to tip creators and collect NFTs</p>
                        <button
                            className="btn btn-lg btn-primary"
                            onClick={handleConnect}
                            disabled={connecting}
                        >
                            {connecting ? (
                                <><span className="spinner" style={{ width: 18, height: 18 }} /> Connecting...</>
                            ) : (
                                <>🔗 Connect Pera Wallet</>
                            )}
                        </button>
                    </div>
                </section>
            )}

            {/* ── FUND WALLET ── */}
            {isAuthenticated && (
                <section className="fund-section">
                    <div className="card">
                        <h2 style={{ marginBottom: 8 }}>💰 Fund Your Wallet</h2>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 16 }}>
                            Get TestNet ALGO for testing. Maximum 10 ALGO per request.
                        </p>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <input
                                type="number"
                                value={fundAmount}
                                onChange={(e) => setFundAmount(e.target.value)}
                                min="0.1"
                                max="10"
                                step="0.5"
                                style={{ maxWidth: 100 }}
                            />
                            <span style={{ color: 'var(--text-secondary)' }}>ALGO</span>
                            <button
                                className="btn btn-primary"
                                onClick={handleFund}
                                disabled={funding}
                            >
                                {funding ? 'Funding...' : 'Fund Wallet'}
                            </button>
                        </div>
                    </div>
                </section>
            )}

            {/* ── QUICK ACTIONS ── */}
            {isAuthenticated && (
                <div className="quick-actions">
                    {role === 'creator' && (
                        <Link to="/creator" className="btn btn-lg btn-primary">
                            ⚡ Creator Hub
                        </Link>
                    )}
                    {role === 'fan' && (
                        <Link to="/creator" className="btn btn-lg btn-secondary"
                            onClick={(e) => {
                                e.preventDefault();
                                navigate('/fan');
                            }}
                        >
                            🎒 My Collection
                        </Link>
                    )}
                    <Link to="/explore" className="btn btn-lg btn-secondary">
                        🔍 Explore Creators
                    </Link>
                    <Link to="/fan" className="btn btn-lg btn-secondary">
                        📦 My NFTs
                    </Link>
                </div>
            )}

            {/* ── HEALTH ── */}
            {health && (
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                    <span className={`badge ${health.algorand_connected ? 'badge-success' : 'badge-danger'}`}>
                        {health.algorand_connected ? '● Algorand TestNet Connected' : '● Disconnected'}
                        {health.last_round && ` — Round #${health.last_round}`}
                    </span>
                </div>
            )}
        </div>
    );
}
