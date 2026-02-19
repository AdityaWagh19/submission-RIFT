import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { merchApi } from '../api/merch';
import { bauniApi, shawtyApi } from '../api/loyalty';
import Modal from '../components/Modal';
import { truncateWallet } from '../utils/helpers';

export default function Store() {
    const { creatorWallet } = useParams();
    const { wallet, isAuthenticated } = useAuth();
    const toast = useToast();

    const [products, setProducts] = useState([]);
    const [membersOnly, setMembersOnly] = useState([]);
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState('all');
    const [cart, setCart] = useState([]);
    const [showCart, setShowCart] = useState(false);
    const [quote, setQuote] = useState(null);
    const [membership, setMembership] = useState(null);
    const [shawtyTokens, setShawtyTokens] = useState([]);
    const [selectedShawty, setSelectedShawty] = useState([]);

    useEffect(() => {
        setLoading(true);
        const promises = [
            merchApi.getStoreCatalog(creatorWallet).catch(() => ({ data: [] })),
        ];
        if (isAuthenticated && wallet) {
            promises.push(bauniApi.getMembershipStatus(wallet, creatorWallet).catch(() => null));
            promises.push(merchApi.getFanOrders(wallet).catch(() => ({ data: [] })));
            promises.push(shawtyApi.getTokens(wallet).catch(() => ({ data: [] })));
        }
        Promise.all(promises).then(([catalog, mem, fanOrders, tokens]) => {
            setProducts(catalog.data || []);
            if (mem) setMembership(mem);
            if (fanOrders) setOrders(fanOrders.data || []);
            if (tokens) setShawtyTokens(tokens.data?.tokens || tokens.tokens || tokens.data || []);
        }).finally(() => setLoading(false));
    }, [creatorWallet, wallet, isAuthenticated]);

    const loadMembersOnly = async () => {
        if (!wallet) { toast.error('Connect wallet first'); return; }
        try {
            const res = await merchApi.getMembersOnlyCatalog(creatorWallet, wallet);
            setMembersOnly(res.data || []);
            setTab('members');
        } catch (err) { toast.error(err.message); }
    };

    const addToCart = (product) => {
        setCart((prev) => {
            const existing = prev.find((c) => c.productId === product.id);
            if (existing) return prev.map((c) => c.productId === product.id ? { ...c, quantity: c.quantity + 1 } : c);
            return [...prev, { productId: product.id, quantity: 1, name: product.name, price: product.price_algo }];
        });
        toast.success(`Added ${product.name} to cart`);
    };

    const removeFromCart = (productId) => {
        setCart((prev) => prev.filter((c) => c.productId !== productId));
    };

    const getQuote = async () => {
        if (!wallet) { toast.error('Connect wallet first'); return; }
        try {
            const res = await merchApi.getQuote(creatorWallet, {
                fanWallet: wallet,
                items: cart.map((c) => ({ productId: c.productId, quantity: c.quantity })),
                shawtyAssetIds: selectedShawty,
            });
            setQuote(res.data || res);
        } catch (err) { toast.error(err.message); }
    };

    const placeOrder = async () => {
        if (!wallet) { toast.error('Connect wallet first'); return; }
        try {
            await merchApi.createOrder(creatorWallet, {
                fanWallet: wallet,
                items: cart.map((c) => ({ productId: c.productId, quantity: c.quantity })),
                shawtyAssetIds: selectedShawty,
            });
            toast.success('Order placed!');
            setCart([]);
            setQuote(null);
            setShowCart(false);
            const fanOrders = await merchApi.getFanOrders(wallet);
            setOrders(fanOrders.data || []);
        } catch (err) { toast.error(err.message); }
    };

    if (loading) return <div className="page-container"><div className="loading-center"><div className="spinner" /></div></div>;

    const displayProducts = tab === 'members' ? membersOnly : products;

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1>🛍️ Creator Store</h1>
                    <p className="page-subtitle">{truncateWallet(creatorWallet)}</p>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {membership?.is_valid && <span className="badge badge-success">🎫 Member</span>}
                    {cart.length > 0 && (
                        <button className="btn btn-primary btn-sm" onClick={() => setShowCart(true)}>
                            🛒 Cart ({cart.length})
                        </button>
                    )}
                    <Link to={`/tip/${creatorWallet}`} className="btn btn-secondary btn-sm">💸 Tip</Link>
                    <Link to="/explore" className="btn btn-secondary btn-sm">← Back</Link>
                </div>
            </div>

            <div className="tab-bar" style={{ maxWidth: 300 }}>
                <button className={`tab-btn ${tab === 'all' ? 'active' : ''}`} onClick={() => setTab('all')}>All Products</button>
                <button className={`tab-btn ${tab === 'members' ? 'active' : ''}`} onClick={loadMembersOnly}>Members Only</button>
            </div>

            {displayProducts.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">🛍️</div>
                    <p className="empty-text">{tab === 'members' ? 'No members-only products' : 'No products in this store yet'}</p>
                </div>
            ) : (
                <div className="nft-grid">
                    {displayProducts.map((p, i) => (
                        <div key={i} className="card" style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>📦</div>
                            <h3 style={{ fontSize: '1rem', marginBottom: 4 }}>{p.name}</h3>
                            {p.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 8 }}>{p.description}</p>}
                            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-cyan)', marginBottom: 8 }}>{p.price_algo} ALGO</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 12 }}>
                                Stock: {p.stock_quantity ?? '∞'}
                            </div>
                            <button className="btn btn-primary btn-sm" onClick={() => addToCart(p)}>Add to Cart</button>
                        </div>
                    ))}
                </div>
            )}

            {/* Cart Drawer */}
            <Modal isOpen={showCart} onClose={() => setShowCart(false)} title="🛒 Your Cart">
                {cart.length === 0 ? (
                    <p style={{ color: 'var(--text-secondary)' }}>Cart is empty</p>
                ) : (
                    <div>
                        {cart.map((item, i) => (
                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                                <div>
                                    <div style={{ fontWeight: 600 }}>{item.name}</div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Qty: {item.quantity} · {item.price} ALGO each</div>
                                </div>
                                <button className="btn btn-danger btn-sm" onClick={() => removeFromCart(item.productId)}>✕</button>
                            </div>
                        ))}

                        {shawtyTokens.length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                <label className="form-label">Apply Shawty Discount</label>
                                <select multiple value={selectedShawty} onChange={(e) => setSelectedShawty([...e.target.selectedOptions].map(o => parseInt(o.value)))}
                                    style={{ height: 60 }}>
                                    {shawtyTokens.filter(t => !t.is_burned && !t.is_locked).map((t, i) => (
                                        <option key={i} value={t.asset_id}>Token #{t.asset_id}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                            <button className="btn btn-secondary" onClick={getQuote}>Get Quote</button>
                            <button className="btn btn-primary" onClick={placeOrder}>Place Order</button>
                        </div>

                        {quote && (
                            <div className="card" style={{ marginTop: 16, background: 'var(--accent-green-dim)' }}>
                                <div style={{ fontSize: '0.85rem' }}>
                                    <div>Subtotal: {quote.subtotal_algo ?? quote.subtotal} ALGO</div>
                                    <div>Discount: -{quote.discount_algo ?? quote.discount ?? 0} ALGO</div>
                                    <div style={{ fontWeight: 800, fontSize: '1.1rem', marginTop: 8 }}>Total: {quote.total_algo ?? quote.total} ALGO</div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </Modal>

            {/* Order History */}
            {orders.length > 0 && (
                <div style={{ marginTop: 32 }}>
                    <h3 style={{ marginBottom: 12 }}>📦 Your Orders</h3>
                    <div className="table-container">
                        <table>
                            <thead><tr><th>Order</th><th>Total</th><th>Status</th><th>Date</th></tr></thead>
                            <tbody>
                                {orders.map((o, i) => (
                                    <tr key={i}>
                                        <td>#{o.id}</td>
                                        <td>{o.total_algo} ALGO</td>
                                        <td><span className={`badge ${o.status === 'PAID' ? 'badge-success' : 'badge-warning'}`}>{o.status}</span></td>
                                        <td style={{ color: 'var(--text-muted)' }}>{o.created_at?.slice(0, 10)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
