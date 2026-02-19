import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import { leaderboardApi } from '../api/leaderboard';
import { butkiApi } from '../api/loyalty';
import { truncateWallet } from '../utils/helpers';

export default function Explore() {
    const [creators, setCreators] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null); // creatorWallet
    const [fanLeaderboard, setFanLeaderboard] = useState([]);
    const [butkiLeaderboard, setButkiLeaderboard] = useState([]);
    const [subLoading, setSubLoading] = useState(false);
    const toast = useToast();

    useEffect(() => {
        setLoading(true);
        leaderboardApi.getGlobalTopCreators(50)
            .then((d) => setCreators(d.data?.leaderboard || d.leaderboard || []))
            .catch((e) => toast.error(e.message))
            .finally(() => setLoading(false));
    }, []);

    const toggleExpand = async (creatorWallet) => {
        if (expanded === creatorWallet) {
            setExpanded(null);
            return;
        }
        setExpanded(creatorWallet);
        setSubLoading(true);
        try {
            const [fans, butki] = await Promise.all([
                leaderboardApi.getCreatorLeaderboard(creatorWallet, 10).catch(() => ({ data: { leaderboard: [] } })),
                butkiApi.getLeaderboard(creatorWallet, 10).catch(() => ({ leaderboard: [] })),
            ]);
            setFanLeaderboard(fans.data?.leaderboard || fans.leaderboard || []);
            setButkiLeaderboard(butki.data?.leaderboard || butki.leaderboard || []);
        } catch (e) { toast.error(e.message); }
        finally { setSubLoading(false); }
    };

    if (loading) return <div className="page-container"><div className="loading-center"><div className="spinner" /></div></div>;

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1>🏆 Explore Creators</h1>
                    <p className="page-subtitle">Top creators on Algorand ranked by total ALGO received</p>
                </div>
            </div>

            {creators.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">🔍</div>
                    <p className="empty-text">No creators yet. Be the first!</p>
                    <Link to="/creator" className="btn btn-primary">Become a Creator</Link>
                </div>
            ) : (
                <div>
                    {creators.map((c, i) => (
                        <div key={i} style={{ marginBottom: 8 }}>
                            <div className="card" style={{ cursor: 'pointer' }} onClick={() => toggleExpand(c.creator_wallet || c.creatorWallet)}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                                    <span style={{ fontWeight: 900, fontSize: '1.2rem', color: i === 0 ? 'var(--accent-gold)' : i === 1 ? 'var(--text-secondary)' : 'var(--text-muted)', minWidth: 30 }}>
                                        #{c.rank || i + 1}
                                    </span>
                                    <div style={{ flex: 1, minWidth: 150 }}>
                                        <div style={{ fontWeight: 700 }}>{c.username || truncateWallet(c.creator_wallet || c.creatorWallet)}</div>
                                        <div className="wallet-addr" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            {truncateWallet(c.creator_wallet || c.creatorWallet)}
                                        </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontWeight: 800, color: 'var(--accent-cyan)' }}>
                                            {Number(c.total_algo_received || c.totalAlgoReceived || 0).toFixed(2)} ALGO
                                        </div>
                                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                            {c.tip_count || c.tipCount || 0} tips · {c.unique_fans || c.uniqueFans || 0} fans
                                        </div>
                                    </div>
                                    <span style={{ color: 'var(--text-muted)', fontSize: '1.2rem' }}>
                                        {expanded === (c.creator_wallet || c.creatorWallet) ? '▲' : '▼'}
                                    </span>
                                </div>
                            </div>

                            {expanded === (c.creator_wallet || c.creatorWallet) && (
                                <div className="card-glass" style={{ marginTop: 4, padding: 20 }}>
                                    {subLoading ? (
                                        <div className="loading-center" style={{ padding: 20 }}><div className="spinner" /></div>
                                    ) : (
                                        <div style={{ display: 'grid', gap: 20, gridTemplateColumns: '1fr 1fr' }}>
                                            {/* Fan Leaderboard by ALGO */}
                                            <div>
                                                <h4 style={{ marginBottom: 10 }}>💎 Top Fans by ALGO</h4>
                                                {fanLeaderboard.length === 0 ? (
                                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No fans yet</p>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                                        {fanLeaderboard.map((f, j) => (
                                                            <div key={j} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.85rem' }}>
                                                                <span>#{f.rank || j + 1} {truncateWallet(f.fan_wallet || f.fanWallet)}</span>
                                                                <span style={{ color: 'var(--accent-cyan)' }}>{Number(f.total_algo_tipped || f.totalAlgoTipped || 0).toFixed(2)} ALGO</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Butki Leaderboard */}
                                            <div>
                                                <h4 style={{ marginBottom: 10 }}>🏆 Top Fans by Badges</h4>
                                                {butkiLeaderboard.length === 0 ? (
                                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No badges yet</p>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                                        {butkiLeaderboard.map((f, j) => (
                                                            <div key={j} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.85rem' }}>
                                                                <span>#{f.rank || j + 1} {truncateWallet(f.fan_wallet || f.fanWallet)}</span>
                                                                <span style={{ color: 'var(--accent-gold)' }}>{f.butki_badges_earned || f.butkiBadgesEarned} 🏆</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                                        <Link to={`/store/${c.creator_wallet || c.creatorWallet}`} className="btn btn-secondary btn-sm">🛍️ View Store</Link>
                                        <Link to={`/tip/${c.creator_wallet || c.creatorWallet}`} className="btn btn-primary btn-sm">💸 Tip Creator</Link>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
