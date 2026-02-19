import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { creatorApi } from '../api/creator';
import TabPanel from '../components/TabPanel';
import Modal from '../components/Modal';
import { truncateWallet, microToAlgo, formatDate, timeAgo } from '../utils/helpers';

/* ══════════════════════════════════════════════════════════
   TAB 1: Dashboard
   ══════════════════════════════════════════════════════════ */
function DashboardTab({ wallet }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const toast = useToast();

    useEffect(() => {
        if (!wallet) return;
        setLoading(true);
        creatorApi.getDashboard(wallet)
            .then((d) => setData(d.data || d))
            .catch((e) => toast.error(e.message))
            .finally(() => setLoading(false));
    }, [wallet]);

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;
    if (!data) return <div className="empty-state"><div className="empty-icon">📊</div><p className="empty-text">No dashboard data yet</p></div>;

    const stats = data.stats || {};
    const contract = data.contract || {};
    const txns = data.recent_transactions || data.recentTransactions || [];

    return (
        <div>
            <div className="stat-grid">
                <div className="stat-card">
                    <span className="stat-icon">💸</span>
                    <span className="stat-value">{stats.total_tips ?? stats.totalTips ?? 0}</span>
                    <span className="stat-label">Total Tips</span>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">💎</span>
                    <span className="stat-value">{(stats.total_algo_received ?? stats.totalAmountAlgo) != null ? Number(stats.total_algo_received ?? stats.totalAmountAlgo).toFixed(2) : '0.00'}</span>
                    <span className="stat-label">ALGO Earned</span>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">👥</span>
                    <span className="stat-value">{stats.unique_fans ?? data.totalFans ?? data.total_fans ?? 0}</span>
                    <span className="stat-label">Fans</span>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">🖼️</span>
                    <span className="stat-value">{stats.nfts_minted ?? data.totalStickersMinted ?? data.total_stickers_minted ?? 0}</span>
                    <span className="stat-label">NFTs Minted</span>
                </div>
            </div>

            {(contract.app_id || contract.appId) && (
                <div className="card" style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Contract</span>
                            <div style={{ fontWeight: 700 }}>App ID: {contract.app_id || contract.appId}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{truncateWallet(contract.app_address || contract.appAddress)}</div>
                        </div>
                        <span className={`badge ${contract.active ? 'badge-success' : 'badge-danger'}`}>
                            {contract.active ? 'Active' : 'Paused'} · v{contract.version ?? 1}
                        </span>
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
                <Link to={`/store/${wallet}`} className="btn btn-secondary btn-sm">🛍️ View Store</Link>
                <Link to="/explore" className="btn btn-secondary btn-sm">🏆 Leaderboard</Link>
                <Link to={`/tip/${wallet}`} className="btn btn-secondary btn-sm">💸 Test Tip</Link>
            </div>

            {txns.length > 0 && (
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Fan</th>
                                <th>Amount</th>
                                <th>Memo</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {txns.slice(0, 10).map((tx, i) => (
                                <tr key={i}>
                                    <td className="wallet-addr">{truncateWallet(tx.fan_wallet)}</td>
                                    <td>{tx.amount_algo ? Number(tx.amount_algo).toFixed(2) : microToAlgo(tx.amount_micro)} ALGO</td>
                                    <td style={{ color: 'var(--text-secondary)' }}>{tx.memo || '—'}</td>
                                    <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{timeAgo(tx.detected_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   TAB 2: Sticker Templates
   ══════════════════════════════════════════════════════════ */
function TemplatesTab({ wallet }) {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [form, setForm] = useState({ name: '', category: '', sticker_type: 'soulbound', tip_threshold: '1.0' });
    const [image, setImage] = useState(null);
    const [creating, setCreating] = useState(false);
    const toast = useToast();

    const fetchTemplates = () => {
        setLoading(true);
        creatorApi.getTemplates(wallet)
            .then((d) => setTemplates(d.data || d.templates || []))
            .catch((e) => toast.error(e.message))
            .finally(() => setLoading(false));
    };

    useEffect(() => { if (wallet) fetchTemplates(); }, [wallet]);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!image) { toast.error('Please select an image'); return; }
        setCreating(true);
        try {
            const fd = new FormData();
            fd.append('name', form.name);
            fd.append('category', form.category || 'general');
            fd.append('sticker_type', form.sticker_type);
            fd.append('tip_threshold', form.tip_threshold);
            fd.append('image', image);
            await creatorApi.createTemplate(wallet, fd);
            toast.success('Template created!');
            setShowCreate(false);
            setForm({ name: '', category: '', sticker_type: 'soulbound', tip_threshold: '1.0' });
            setImage(null);
            fetchTemplates();
        } catch (err) {
            toast.error(err.message);
        } finally {
            setCreating(false);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this template?')) return;
        try {
            await creatorApi.deleteTemplate(wallet, id);
            toast.success('Template deleted');
            fetchTemplates();
        } catch (err) {
            toast.error(err.message);
        }
    };

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <h3>Sticker Templates ({templates.length})</h3>
                <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>+ Create Template</button>
            </div>

            {templates.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">🎨</div>
                    <p className="empty-text">No templates yet. Create your first sticker!</p>
                </div>
            ) : (
                <div className="nft-grid">
                    {templates.map((t) => (
                        <div key={t.id} className="nft-card">
                            <div className="nft-image" style={{ background: `url(${t.image_url || ''}) center/cover, var(--bg-secondary)`, height: 160 }} />
                            <div className="nft-info">
                                <div className="nft-name">{t.name}</div>
                                <span className={`nft-type ${t.sticker_type}`}>{t.sticker_type}</span>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
                                    {t.mint_count ?? 0} minted · ≥{t.tip_threshold} ALGO
                                </div>
                                {(t.mint_count ?? 0) === 0 && (
                                    <button className="btn btn-danger btn-sm" style={{ marginTop: 8 }} onClick={() => handleDelete(t.id)}>🗑️ Delete</button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Sticker Template">
                <form onSubmit={handleCreate}>
                    <div className="form-group">
                        <label className="form-label">Name</label>
                        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="My Cool Sticker" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Type</label>
                        <select value={form.sticker_type} onChange={(e) => setForm({ ...form, sticker_type: e.target.value })}>
                            <option value="soulbound">Soulbound (Loyalty / Membership)</option>
                            <option value="golden">Golden (Collectible / Tradeable)</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Category</label>
                        <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="general" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Min Tip (ALGO)</label>
                        <input type="number" value={form.tip_threshold} onChange={(e) => setForm({ ...form, tip_threshold: e.target.value })} step="0.1" min="0" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Image</label>
                        <input type="file" accept="image/*" onChange={(e) => setImage(e.target.files[0])} required />
                    </div>
                    <div className="form-actions">
                        <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                        <button type="submit" className="btn btn-primary" disabled={creating}>{creating ? 'Creating...' : 'Create'}</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   TAB 3: Products & Discounts
   ══════════════════════════════════════════════════════════ */
function ProductsTab({ wallet }) {
    const [products, setProducts] = useState([]);
    const [discounts, setDiscounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showProduct, setShowProduct] = useState(false);
    const [showDiscount, setShowDiscount] = useState(false);
    const [productForm, setProductForm] = useState({ slug: '', name: '', description: '', price_algo: '', stock_quantity: '', active: true });
    const [discountForm, setDiscountForm] = useState({ discountType: 'PERCENT', value: '', minShawtyTokens: '0', requiresBauni: false });
    const toast = useToast();

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [p, d] = await Promise.all([
                creatorApi.getProducts(wallet),
                creatorApi.getDiscounts(wallet),
            ]);
            setProducts(p.data || p.products || []);
            setDiscounts(d.data || d.rules || []);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    };

    useEffect(() => { if (wallet) fetchAll(); }, [wallet]);

    const handleCreateProduct = async (e) => {
        e.preventDefault();
        try {
            await creatorApi.createProduct(wallet, {
                ...productForm,
                price_algo: parseFloat(productForm.price_algo),
                stock_quantity: productForm.stock_quantity ? parseInt(productForm.stock_quantity) : null,
            });
            toast.success('Product created!');
            setShowProduct(false);
            setProductForm({ slug: '', name: '', description: '', price_algo: '', stock_quantity: '', active: true });
            fetchAll();
        } catch (err) { toast.error(err.message); }
    };

    const handleDeleteProduct = async (id) => {
        if (!confirm('Delete this product?')) return;
        try {
            await creatorApi.deleteProduct(wallet, id);
            toast.success('Product deleted');
            fetchAll();
        } catch (err) { toast.error(err.message); }
    };

    const handleToggleActive = async (id, active) => {
        try {
            await creatorApi.updateProduct(wallet, id, { active: !active });
            fetchAll();
        } catch (err) { toast.error(err.message); }
    };

    const handleCreateDiscount = async (e) => {
        e.preventDefault();
        try {
            await creatorApi.createDiscount(wallet, {
                ...discountForm,
                value: parseFloat(discountForm.value),
                minShawtyTokens: parseInt(discountForm.minShawtyTokens),
            });
            toast.success('Discount rule created!');
            setShowDiscount(false);
            setDiscountForm({ discountType: 'PERCENT', value: '', minShawtyTokens: '0', requiresBauni: false });
            fetchAll();
        } catch (err) { toast.error(err.message); }
    };

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;

    return (
        <div>
            {/* Products */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3>Products ({products.length})</h3>
                <button className="btn btn-primary btn-sm" onClick={() => setShowProduct(true)}>+ Add Product</button>
            </div>

            {products.length > 0 ? (
                <div className="table-container" style={{ marginBottom: 32 }}>
                    <table>
                        <thead><tr><th>Name</th><th>Slug</th><th>Price</th><th>Stock</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody>
                            {products.map((p) => (
                                <tr key={p.id}>
                                    <td style={{ fontWeight: 600 }}>{p.name}</td>
                                    <td style={{ color: 'var(--text-muted)' }}>{p.slug}</td>
                                    <td>{p.price_algo} ALGO</td>
                                    <td>{p.stock_quantity ?? '∞'}</td>
                                    <td>
                                        <button className={`badge ${p.active ? 'badge-success' : 'badge-danger'}`} onClick={() => handleToggleActive(p.id, p.active)}>
                                            {p.active ? 'Active' : 'Inactive'}
                                        </button>
                                    </td>
                                    <td>
                                        <button className="btn btn-danger btn-sm" onClick={() => handleDeleteProduct(p.id)}>🗑️</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="empty-state" style={{ padding: '30px 0' }}><p className="empty-text">No products yet</p></div>
            )}

            {/* Discounts */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3>Discount Rules ({discounts.length})</h3>
                <button className="btn btn-primary btn-sm" onClick={() => setShowDiscount(true)}>+ Add Discount</button>
            </div>

            {discounts.length > 0 ? (
                <div className="table-container">
                    <table>
                        <thead><tr><th>Type</th><th>Value</th><th>Min Shawty</th><th>Bauni Required</th></tr></thead>
                        <tbody>
                            {discounts.map((d, i) => (
                                <tr key={i}>
                                    <td><span className="badge badge-purple">{d.discount_type}</span></td>
                                    <td>{d.value}{d.discount_type === 'PERCENT' ? '%' : ' ALGO'}</td>
                                    <td>{d.min_shawty_tokens} tokens</td>
                                    <td>{d.requires_bauni ? '✅ Yes' : 'No'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="empty-state" style={{ padding: '30px 0' }}><p className="empty-text">No discount rules</p></div>
            )}

            {/* Product Modal */}
            <Modal isOpen={showProduct} onClose={() => setShowProduct(false)} title="Add Product">
                <form onSubmit={handleCreateProduct}>
                    <div className="form-group">
                        <label className="form-label">Name</label>
                        <input value={productForm.name} onChange={(e) => setProductForm({ ...productForm, name: e.target.value })} required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Slug (URL-friendly)</label>
                        <input value={productForm.slug} onChange={(e) => setProductForm({ ...productForm, slug: e.target.value })} required placeholder="cool-tshirt" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Description</label>
                        <textarea value={productForm.description} onChange={(e) => setProductForm({ ...productForm, description: e.target.value })} rows={2} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Price (ALGO)</label>
                        <input type="number" value={productForm.price_algo} onChange={(e) => setProductForm({ ...productForm, price_algo: e.target.value })} step="0.1" min="0.01" required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Stock (leave empty for unlimited)</label>
                        <input type="number" value={productForm.stock_quantity} onChange={(e) => setProductForm({ ...productForm, stock_quantity: e.target.value })} min="0" />
                    </div>
                    <div className="form-actions">
                        <button type="button" className="btn btn-secondary" onClick={() => setShowProduct(false)}>Cancel</button>
                        <button type="submit" className="btn btn-primary">Create</button>
                    </div>
                </form>
            </Modal>

            {/* Discount Modal */}
            <Modal isOpen={showDiscount} onClose={() => setShowDiscount(false)} title="Add Discount Rule">
                <form onSubmit={handleCreateDiscount}>
                    <div className="form-group">
                        <label className="form-label">Type</label>
                        <select value={discountForm.discountType} onChange={(e) => setDiscountForm({ ...discountForm, discountType: e.target.value })}>
                            <option value="PERCENT">Percentage</option>
                            <option value="FIXED_ALGO">Fixed ALGO</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Value</label>
                        <input type="number" value={discountForm.value} onChange={(e) => setDiscountForm({ ...discountForm, value: e.target.value })} step="0.1" min="0.01" required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Min Shawty Tokens Required</label>
                        <input type="number" value={discountForm.minShawtyTokens} onChange={(e) => setDiscountForm({ ...discountForm, minShawtyTokens: e.target.value })} min="0" />
                    </div>
                    <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="checkbox" checked={discountForm.requiresBauni} onChange={(e) => setDiscountForm({ ...discountForm, requiresBauni: e.target.checked })} style={{ width: 'auto' }} />
                        <label className="form-label" style={{ marginBottom: 0 }}>Requires Bauni Membership</label>
                    </div>
                    <div className="form-actions">
                        <button type="button" className="btn btn-secondary" onClick={() => setShowDiscount(false)}>Cancel</button>
                        <button type="submit" className="btn btn-primary">Create</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   TAB 4: Contract Management
   ══════════════════════════════════════════════════════════ */
function ContractTab({ wallet }) {
    const [contract, setContract] = useState(null);
    const [contractStats, setContractStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [acting, setActing] = useState(false);
    const toast = useToast();

    const fetchContract = async () => {
        setLoading(true);
        try {
            const [c, s] = await Promise.all([
                creatorApi.getContract(wallet).catch(() => null),
                creatorApi.getContractStats(wallet).catch(() => null),
            ]);
            setContract(c?.data || c);
            setContractStats(s?.data || s);
        } catch { setContract(null); }
        finally { setLoading(false); }
    };

    useEffect(() => { if (wallet) fetchContract(); }, [wallet]);

    const handleUpgrade = async () => {
        if (!confirm('Deploy a new contract version?')) return;
        setActing(true);
        try {
            await creatorApi.upgradeContract(wallet);
            toast.success('Contract upgraded!');
            fetchContract();
        } catch (err) { toast.error(err.message); }
        finally { setActing(false); }
    };

    const handlePause = async () => {
        if (!confirm('Pause your contract? No tips will be accepted.')) return;
        setActing(true);
        try {
            await creatorApi.pauseContract(wallet);
            toast.success('Contract paused');
            fetchContract();
        } catch (err) { toast.error(err.message); }
        finally { setActing(false); }
    };

    const handleUnpause = async () => {
        setActing(true);
        try {
            await creatorApi.unpauseContract(wallet);
            toast.success('Contract unpaused');
            fetchContract();
        } catch (err) { toast.error(err.message); }
        finally { setActing(false); }
    };

    if (loading) return <div className="loading-center"><div className="spinner" /></div>;
    if (!contract) return <div className="empty-state"><div className="empty-icon">📄</div><p className="empty-text">No active contract. Register as a creator first.</p></div>;

    const appId = contract.app_id || contract.appId;
    const appAddr = contract.app_address || contract.appAddress;
    const isActive = contract.active !== false;

    return (
        <div>
            <div className="card" style={{ marginBottom: 16 }}>
                <h3 style={{ marginBottom: 16 }}>TipProxy Contract</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                    <div><span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>App ID</span><div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{appId}</div></div>
                    <div><span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Version</span><div style={{ fontWeight: 700 }}>{contract.version ?? 1}</div></div>
                    <div style={{ gridColumn: 'span 2' }}><span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Address</span><div className="wallet-addr">{appAddr}</div></div>
                    <div><span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Status</span>
                        <div><span className={`badge ${isActive ? 'badge-success' : 'badge-danger'}`}>{isActive ? 'Active' : 'Paused'}</span></div>
                    </div>
                    {contract.deployed_at || contract.deployedAt ? (
                        <div><span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Deployed</span><div style={{ fontSize: '0.85rem' }}>{formatDate(contract.deployed_at || contract.deployedAt)}</div></div>
                    ) : null}
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {isActive ? (
                        <button className="btn btn-danger btn-sm" onClick={handlePause} disabled={acting}>⏸ Pause Contract</button>
                    ) : (
                        <button className="btn btn-primary btn-sm" onClick={handleUnpause} disabled={acting}>▶ Unpause Contract</button>
                    )}
                    <button className="btn btn-primary btn-sm" onClick={handleUpgrade} disabled={acting}>⬆️ Upgrade</button>
                </div>
            </div>

            {contractStats && (
                <div className="card">
                    <h3 style={{ marginBottom: 16 }}>On-Chain Stats</h3>
                    <div className="stat-grid">
                        <div className="stat-card">
                            <span className="stat-icon">💸</span>
                            <span className="stat-value">{contractStats.total_tips ?? contractStats.totalTips ?? 0}</span>
                            <span className="stat-label">Total Tips</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">💎</span>
                            <span className="stat-value">{Number(contractStats.total_amount_algo ?? contractStats.totalAmountAlgo ?? 0).toFixed(2)}</span>
                            <span className="stat-label">Total ALGO</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">⚙️</span>
                            <span className="stat-value">{contractStats.min_tip_algo ?? contractStats.minTipAlgo ?? '—'}</span>
                            <span className="stat-label">Min Tip (ALGO)</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">📋</span>
                            <span className="stat-value">v{contractStats.contract_version ?? contractStats.contractVersion ?? '?'}</span>
                            <span className="stat-label">Contract Version</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════
   MAIN: Creator Hub Page
   ══════════════════════════════════════════════════════════ */
export default function CreatorHub() {
    const { wallet, role, isAuthenticated, updateRole } = useAuth();
    const toast = useToast();
    const navigate = useNavigate();
    const [registering, setRegistering] = useState(false);

    useEffect(() => {
        if (!isAuthenticated) navigate('/');
    }, [isAuthenticated, navigate]);

    const handleRegister = async () => {
        setRegistering(true);
        try {
            await creatorApi.register(wallet);
            toast.success('Registered as creator!');
            updateRole('creator');
        } catch (err) {
            toast.error(err.message);
        } finally {
            setRegistering(false);
        }
    };

    if (!isAuthenticated) return null;

    // Show register prompt if not a creator yet
    if (role !== 'creator') {
        return (
            <div className="page-container">
                <div className="connect-section">
                    <div className="connect-card card-glass" style={{ textAlign: 'center' }}>
                        <h2>Become a Creator</h2>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
                            Register to deploy your TipProxy contract and start receiving tips.
                        </p>
                        <button className="btn btn-lg btn-primary" onClick={handleRegister} disabled={registering}>
                            {registering ? 'Deploying Contract...' : '🚀 Register as Creator'}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1>Creator Hub</h1>
                    <p className="page-subtitle">Manage your store, templates, and smart contract</p>
                </div>
                <span className="wallet-badge">
                    <span className="wallet-dot" />
                    <span className="wallet-addr">{truncateWallet(wallet)}</span>
                </span>
            </div>

            <TabPanel tabs={[
                { label: '📊 Dashboard', content: <DashboardTab wallet={wallet} /> },
                { label: '🎨 Templates', content: <TemplatesTab wallet={wallet} /> },
                { label: '🛍️ Products', content: <ProductsTab wallet={wallet} /> },
                { label: '📄 Contract', content: <ContractTab wallet={wallet} /> },
            ]} />
        </div>
    );
}
