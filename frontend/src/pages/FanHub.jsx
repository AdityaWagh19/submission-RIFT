import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { fanApi } from '../api/fan';
import { nftApi } from '../api/nft';
import { butkiApi, bauniApi, shawtyApi } from '../api/loyalty';
import TabPanel from '../components/TabPanel';
import Modal from '../components/Modal';
import { truncateWallet, microToAlgo, formatDate, timeAgo } from '../utils/helpers';

/* ══════════════════════════════════════════════════════════
   TAB 1: My NFTs
   ══════════════════════════════════════════════════════════ */
function NFTsTab({ wallet }) {
    const [nfts, setNfts] = useState([]);
    const [pending, setPending] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedNft, setSelectedNft] = useState(null);
    const toast = useToast();

    useEffect(() => {
        if (!wallet) return;
        setLoading(true);
        Promise.all([
            fanApi.getInventory(wallet).catch(() => ({ data: [] })),
            fanApi.getPending(wallet).catch(() => ({ data: { pending: [] } })),
        ]).then(([inv, pend]) => {
            setNfts(inv.data || []);
            setPending(pend.data?.pending || pend.pending || []);
        }).finally(() => setLoading(false));
    }, [wallet]);

    const handleClaim = async (nftId) => {
        try {
            await fanApi.claimNFT(wallet, nftId);
            toast.success('NFT claimed!');
            // Refresh
            const inv = await fanApi.getInventory(wallet);
            setNfts(inv.data || []);
            const pend = await fanApi.getPending(wallet);
            setPending(pend.data?.pending || pend.pending || []);
        } catch (err) { toast.error(err.message); }
    };

    const viewDetail = async (assetId) => {
        try {
            const detail = await nftApi.getDetails(assetId);
            setSelectedNft(detail.data || detail);
        } catch (err) { toast.error(err.message); }
    };

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;

    return (
        <div>
            {pending.length > 0 && (
                <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent-gold)', background: 'var(--accent-gold-dim)' }}>
                    <h3>⚡ {pending.length} NFT{pending.length > 1 ? 's' : ''} awaiting claim</h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>Opt-in to receive these NFTs</p>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {pending.map((p, i) => (
                            <button key={i} className="btn btn-primary btn-sm" onClick={() => handleClaim(p.id || p.nft_id)}>
                                Claim #{p.asset_id || p.id}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {nfts.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">🖼️</div>
                    <p className="empty-text">No NFTs yet. Tip a creator to earn stickers!</p>
                    <Link to="/explore" className="btn btn-primary">🔍 Find Creators</Link>
                </div>
            ) : (
                <div className="nft-grid">
                    {nfts.map((nft, i) => (
                        <div key={i} className="nft-card" onClick={() => viewDetail(nft.asset_id)}>
                            <div className="nft-image" style={{ background: `url(${nft.image_url || ''}) center/cover, var(--bg-secondary)` }} />
                            <div className="nft-info">
                                <div className="nft-name">{nft.template_name || nft.name || `NFT #${nft.asset_id}`}</div>
                                <span className={`nft-type ${nft.sticker_type || nft.nft_class || 'shawty'}`}>
                                    {nft.sticker_type || nft.nft_class || 'nft'}
                                </span>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                    {truncateWallet(nft.creator_wallet || '')}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <Modal isOpen={!!selectedNft} onClose={() => setSelectedNft(null)} title="NFT Details">
                {selectedNft && (
                    <div>
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Asset ID</div>
                            <div style={{ fontWeight: 700 }}>{selectedNft.asset_id}</div>
                        </div>
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Type</div>
                            <span className={`nft-type ${selectedNft.sticker_type || ''}`}>{selectedNft.sticker_type || 'NFT'}</span>
                        </div>
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Owner</div>
                            <div className="wallet-addr">{selectedNft.owner_wallet}</div>
                        </div>
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Minted</div>
                            <div>{formatDate(selectedNft.minted_at)}</div>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   TAB 2: Loyalty & Membership
   ══════════════════════════════════════════════════════════ */
function LoyaltyTab({ wallet }) {
    const [loyalty, setLoyalty] = useState(null);
    const [memberships, setMemberships] = useState([]);
    const [loading, setLoading] = useState(true);
    const toast = useToast();

    useEffect(() => {
        if (!wallet) return;
        setLoading(true);
        Promise.all([
            butkiApi.getFanLoyalty(wallet).catch(() => null),
            bauniApi.getAllMemberships(wallet, false).catch(() => ({ memberships: [] })),
        ]).then(([loy, mem]) => {
            setLoyalty(loy);
            setMemberships(mem.memberships || mem.data?.memberships || []);
        }).finally(() => setLoading(false));
    }, [wallet]);

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;

    const creators = loyalty?.creators || [];

    return (
        <div>
            {/* Butki Loyalty */}
            <h3 style={{ marginBottom: 16 }}>🏆 Butki Loyalty</h3>
            {creators.length === 0 ? (
                <div className="empty-state" style={{ padding: '30px 0' }}><p className="empty-text">No loyalty records yet. Start tipping!</p></div>
            ) : (
                <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', marginBottom: 32 }}>
                    {creators.map((c, i) => (
                        <div key={i} className="card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                <div className="wallet-addr" style={{ fontWeight: 600 }}>{truncateWallet(c.creator_wallet)}</div>
                                <span className="badge badge-warning">🏆 {c.butki_badges_earned} badges</span>
                            </div>
                            <div className="progress-bar" style={{ marginBottom: 8 }}>
                                <div className="progress-fill" style={{ width: `${((5 - c.tips_to_next_badge) / 5) * 100}%` }} />
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                {c.tip_count} tips · {Number(c.total_tipped_algo).toFixed(2)} ALGO · {c.tips_to_next_badge} tips to next badge
                            </div>
                            <Link to={`/tip/${c.creator_wallet}`} className="btn btn-sm btn-secondary" style={{ marginTop: 10 }}>💸 Tip</Link>
                        </div>
                    ))}
                </div>
            )}

            {/* Bauni Memberships */}
            <h3 style={{ marginBottom: 16 }}>🎫 Bauni Memberships</h3>
            {memberships.length === 0 ? (
                <div className="empty-state" style={{ padding: '30px 0' }}><p className="empty-text">No memberships yet</p></div>
            ) : (
                <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
                    {memberships.map((m, i) => (
                        <div key={i} className="card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                <div className="wallet-addr" style={{ fontWeight: 600 }}>{truncateWallet(m.creator_wallet)}</div>
                                <span className={`badge ${m.is_active && !m.is_expired ? 'badge-success' : 'badge-danger'}`}>
                                    {m.is_active && !m.is_expired ? 'Active' : 'Expired'}
                                </span>
                            </div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                {m.days_remaining > 0 ? `${m.days_remaining} days left` : 'Expired'}
                                {' · '}{Number(m.amount_paid_algo).toFixed(2)} ALGO paid
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                Expires: {formatDate(m.expires_at)}
                            </div>
                            <Link to={`/store/${m.creator_wallet}`} className="btn btn-sm btn-secondary" style={{ marginTop: 10 }}>🛍️ Store</Link>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   TAB 3: Shawty Tokens
   ══════════════════════════════════════════════════════════ */
function ShawtyTab({ wallet }) {
    const [tokens, setTokens] = useState([]);
    const [redemptions, setRedemptions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAction, setShowAction] = useState(null); // { type: 'burn'|'lock'|'transfer', token }
    const [actionInput, setActionInput] = useState('');
    const toast = useToast();

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [tok, red] = await Promise.all([
                shawtyApi.getTokens(wallet, true),
                shawtyApi.getRedemptions(wallet),
            ]);
            setTokens(tok.data?.tokens || tok.tokens || tok.data || []);
            setRedemptions(red.data?.redemptions || red.redemptions || red.data || []);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    };

    useEffect(() => { if (wallet) fetchAll(); }, [wallet]);

    const handleAction = async () => {
        if (!showAction) return;
        try {
            const { type, token } = showAction;
            if (type === 'burn') {
                await shawtyApi.burnForMerch(wallet, token.asset_id, actionInput);
                toast.success('Token burned for merch!');
            } else if (type === 'lock') {
                await shawtyApi.lockForDiscount(wallet, token.asset_id, actionInput);
                toast.success('Token locked for discount!');
            } else if (type === 'transfer') {
                await shawtyApi.transfer(wallet, actionInput, token.asset_id);
                toast.success('Token transferred!');
            }
            setShowAction(null);
            setActionInput('');
            fetchAll();
        } catch (err) { toast.error(err.message); }
    };

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;

    return (
        <div>
            <h3 style={{ marginBottom: 16 }}>🌟 Shawty Tokens ({tokens.length})</h3>

            {tokens.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">🌟</div>
                    <p className="empty-text">No Shawty tokens yet</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', marginBottom: 32 }}>
                    {tokens.map((t, i) => {
                        const isSpent = t.is_burned || t.is_locked;
                        return (
                            <div key={i} className="card" style={{ opacity: isSpent ? 0.6 : 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <span style={{ fontWeight: 700 }}>Token #{t.asset_id}</span>
                                    <span className={`badge ${t.is_burned ? 'badge-danger' : t.is_locked ? 'badge-warning' : 'badge-success'}`}>
                                        {t.is_burned ? 'Burned' : t.is_locked ? 'Locked' : 'Active'}
                                    </span>
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    Creator: {truncateWallet(t.creator_wallet)}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    {microToAlgo(t.amount_paid_micro)} ALGO · {formatDate(t.purchased_at)}
                                </div>
                                {!isSpent && (
                                    <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                                        <button className="btn btn-danger btn-sm" onClick={() => { setShowAction({ type: 'burn', token: t }); }}>🔥 Burn</button>
                                        <button className="btn btn-secondary btn-sm" onClick={() => { setShowAction({ type: 'lock', token: t }); }}>🔒 Lock</button>
                                        <button className="btn btn-secondary btn-sm" onClick={() => { setShowAction({ type: 'transfer', token: t }); }}>📤 Send</button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Redemption History */}
            {redemptions.length > 0 && (
                <>
                    <h3 style={{ marginBottom: 12 }}>📜 Redemption History</h3>
                    <div className="table-container">
                        <table>
                            <thead><tr><th>Asset</th><th>Type</th><th>Description</th><th>Date</th></tr></thead>
                            <tbody>
                                {redemptions.map((r, i) => (
                                    <tr key={i}>
                                        <td>#{r.shawty_asset_id}</td>
                                        <td><span className="badge badge-info">{r.redemption_type}</span></td>
                                        <td>{r.description}</td>
                                        <td style={{ color: 'var(--text-muted)' }}>{formatDate(r.redeemed_at)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {/* Action Modal */}
            <Modal isOpen={!!showAction} onClose={() => { setShowAction(null); setActionInput(''); }}
                title={showAction?.type === 'burn' ? '🔥 Burn for Merch' : showAction?.type === 'lock' ? '🔒 Lock for Discount' : '📤 Transfer Token'}>
                {showAction && (
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 16 }}>
                            Token #{showAction.token.asset_id}
                        </p>
                        <div className="form-group">
                            <label className="form-label">
                                {showAction.type === 'transfer' ? 'Recipient Wallet Address' : 'Description'}
                            </label>
                            <input value={actionInput} onChange={(e) => setActionInput(e.target.value)} required
                                placeholder={showAction.type === 'transfer' ? '58-char Algorand address' : 'e.g., T-shirt XL'} />
                        </div>
                        <div className="form-actions">
                            <button className="btn btn-secondary" onClick={() => { setShowAction(null); setActionInput(''); }}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleAction}>Confirm</button>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   TAB 4: Stats
   ══════════════════════════════════════════════════════════ */
function StatsTab({ wallet }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const toast = useToast();

    useEffect(() => {
        if (!wallet) return;
        setLoading(true);
        fanApi.getStats(wallet)
            .then((d) => setStats(d.data || d))
            .catch((e) => toast.error(e.message))
            .finally(() => setLoading(false));
    }, [wallet]);

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;
    if (!stats) return <div className="empty-state"><p className="empty-text">No stats yet</p></div>;

    const breakdown = stats.creator_breakdown || stats.creatorBreakdown || [];
    const recent = stats.recent_tips || stats.recentTips || [];

    return (
        <div>
            <div className="stat-grid">
                <div className="stat-card">
                    <span className="stat-icon">💸</span>
                    <span className="stat-value">{stats.total_tips ?? stats.totalTips ?? 0}</span>
                    <span className="stat-label">Total Tips Sent</span>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">💎</span>
                    <span className="stat-value">{Number(stats.total_algo_spent ?? stats.totalAlgoSpent ?? 0).toFixed(2)}</span>
                    <span className="stat-label">ALGO Spent</span>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">👥</span>
                    <span className="stat-value">{stats.unique_creators ?? stats.uniqueCreators ?? 0}</span>
                    <span className="stat-label">Creators Supported</span>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">🖼️</span>
                    <span className="stat-value">{(stats.total_soulbound ?? 0) + (stats.total_golden ?? 0)}</span>
                    <span className="stat-label">NFTs Collected</span>
                </div>
            </div>

            {breakdown.length > 0 && (
                <>
                    <h3 style={{ marginBottom: 12 }}>Per-Creator Breakdown</h3>
                    <div className="table-container" style={{ marginBottom: 24 }}>
                        <table>
                            <thead><tr><th>Creator</th><th>Tips</th><th>ALGO</th><th></th></tr></thead>
                            <tbody>
                                {breakdown.map((c, i) => (
                                    <tr key={i}>
                                        <td className="wallet-addr">{truncateWallet(c.creator_wallet || c.creatorWallet)}</td>
                                        <td>{c.tip_count || c.tipCount}</td>
                                        <td>{Number(c.total_algo || c.totalAlgo || 0).toFixed(2)}</td>
                                        <td><Link to={`/tip/${c.creator_wallet || c.creatorWallet}`} className="btn btn-sm btn-secondary">💸 Tip</Link></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {recent.length > 0 && (
                <>
                    <h3 style={{ marginBottom: 12 }}>Recent Tips</h3>
                    <div className="table-container">
                        <table>
                            <thead><tr><th>Creator</th><th>Amount</th><th>Memo</th><th>Time</th></tr></thead>
                            <tbody>
                                {recent.map((t, i) => (
                                    <tr key={i}>
                                        <td className="wallet-addr">{truncateWallet(t.creator_wallet || t.creatorWallet)}</td>
                                        <td>{Number(t.amount_algo || t.amountAlgo || 0).toFixed(2)} ALGO</td>
                                        <td style={{ color: 'var(--text-secondary)' }}>{t.memo || '—'}</td>
                                        <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{timeAgo(t.detected_at || t.detectedAt)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   MAIN: Fan Hub Page
   ══════════════════════════════════════════════════════════ */
export default function FanHub() {
    const { wallet, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (!isAuthenticated) navigate('/');
    }, [isAuthenticated, navigate]);

    if (!isAuthenticated) return null;

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1>My Collection</h1>
                    <p className="page-subtitle">NFTs, loyalty, memberships, and collectibles</p>
                </div>
                <span className="wallet-badge">
                    <span className="wallet-dot" />
                    <span className="wallet-addr">{truncateWallet(wallet)}</span>
                </span>
            </div>

            <TabPanel tabs={[
                { label: '🖼️ My NFTs', content: <NFTsTab wallet={wallet} /> },
                { label: '🏆 Loyalty', content: <LoyaltyTab wallet={wallet} /> },
                { label: '🌟 Shawty', content: <ShawtyTab wallet={wallet} /> },
                { label: '📊 Stats', content: <StatsTab wallet={wallet} /> },
            ]} />
        </div>
    );
}
