import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import algosdk from 'algosdk';
import { useAuth } from '../context/AuthContext';
import { useWallet } from '../context/WalletContext';
import { useToast } from '../context/ToastContext';
import { creatorApi } from '../api/creator';
import { fanApi } from '../api/fan';
import { butkiApi, bauniApi } from '../api/loyalty';
import { systemApi } from '../api/system';
import { truncateWallet } from '../utils/helpers';

export default function Tip() {
    const { creatorWallet } = useParams();
    const { wallet, isAuthenticated } = useAuth();
    const { signTxn, accounts } = useWallet();
    const senderAddr = wallet || (accounts && accounts[0]);
    const toast = useToast();

    const [contract, setContract] = useState(null);
    const [loyalty, setLoyalty] = useState(null);
    const [membership, setMembership] = useState(null);
    const [goldenOdds, setGoldenOdds] = useState(null);
    const [amount, setAmount] = useState('1.0');
    const [memo, setMemo] = useState('');
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [lastTxId, setLastTxId] = useState(null);

    useEffect(() => {
        setLoading(true);
        const promises = [
            creatorApi.getContract(creatorWallet).catch(() => null),
        ];
        if (isAuthenticated && wallet) {
            promises.push(butkiApi.getFanLoyaltyForCreator(wallet, creatorWallet).catch(() => null));
            promises.push(bauniApi.getMembershipStatus(wallet, creatorWallet).catch(() => null));
            promises.push(fanApi.getGoldenOdds(wallet, parseFloat(amount) || 1.0).catch(() => null));
        }
        Promise.all(promises).then(([con, loy, mem, odds]) => {
            setContract(con?.data || con);
            setLoyalty(loy?.data || loy);
            setMembership(mem?.data || mem);
            setGoldenOdds(odds?.data || odds);
        }).finally(() => setLoading(false));
    }, [creatorWallet, wallet, isAuthenticated]);

    // Update golden odds when amount changes (debounced)
    useEffect(() => {
        if (!isAuthenticated || !wallet) return;
        const timer = setTimeout(() => {
            fanApi.getGoldenOdds(wallet, parseFloat(amount) || 1.0)
                .then((d) => setGoldenOdds(d.data || d))
                .catch(() => { });
        }, 500);
        return () => clearTimeout(timer);
    }, [amount, wallet, isAuthenticated]);

    const handleTip = async () => {
        if (!isAuthenticated) { toast.error('Connect wallet first'); return; }
        if (!senderAddr) { toast.error('No wallet address found'); return; }
        const appId = contract?.app_id || contract?.appId;
        if (!appId) { toast.error('Creator has no active contract'); return; }
        const appAddr = contract.app_address || contract.appAddress;
        if (!appAddr) { toast.error('Cannot find contract address'); return; }

        const tipAlgo = parseFloat(amount);
        if (!tipAlgo || tipAlgo < 0.1) { toast.error('Minimum tip is 0.1 ALGO'); return; }

        setSending(true);
        try {
            // Step 1: Get suggested params directly from Algorand node
            // Using algosdk.Algodv2 gives us a properly typed SuggestedParams object
            const algodClient = new algosdk.Algodv2('', 'https://testnet-api.algonode.cloud', '');
            const sp = await algodClient.getTransactionParams().do();

            const tipMicroAlgo = Math.round(tipAlgo * 1_000_000);

            // Step 2: Build an application call (NoOp) — algosdk v3 API
            // The app call needs extra fee to cover inner transactions in the contract
            const appCallSp = { ...sp, fee: 3000, flatFee: true };
            const appCallTxn = algosdk.makeApplicationCallTxnFromObject({
                sender: senderAddr,
                appIndex: appId,
                onComplete: algosdk.OnApplicationComplete.NoOpOC,
                appArgs: [
                    new Uint8Array(Buffer.from('tip')),
                    ...(memo ? [new Uint8Array(Buffer.from(memo))] : []),
                ],
                suggestedParams: appCallSp,
            });

            // Build a payment to the app address
            const payTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
                sender: senderAddr,
                receiver: appAddr,
                amount: tipMicroAlgo,
                suggestedParams: sp,
            });

            // Group them atomically — payment FIRST (index 0), app call SECOND (index 1)
            // The TipProxy contract expects this order (does `txn GroupIndex - 1`)
            algosdk.assignGroupID([payTxn, appCallTxn]);

            // Step 3: Sign with Pera Wallet
            // Pera SDK expects raw Transaction objects — it encodes internally
            const txnGroup = [payTxn, appCallTxn].map((txn) => ({ txn }));
            const signedTxns = await signTxn(txnGroup);

            // Step 4: Submit to backend
            const signedB64 = signedTxns.map((s) =>
                typeof s === 'string' ? s : Buffer.from(s).toString('base64')
            );

            const submitRes = await systemApi.submitGroup(signedB64);
            const txId = submitRes.txId || submitRes.tx_id || submitRes.data?.txId;
            setLastTxId(txId);

            toast.success(`Tip of ${tipAlgo} ALGO sent! TX: ${txId ? truncateWallet(txId) : 'submitted'}`);

            // Step 5: Refresh loyalty + golden odds
            const [loy, odds] = await Promise.all([
                butkiApi.getFanLoyaltyForCreator(wallet, creatorWallet).catch(() => null),
                fanApi.getGoldenOdds(wallet, parseFloat(amount) || 1.0).catch(() => null),
            ]);
            if (loy) setLoyalty(loy.data || loy);
            if (odds) setGoldenOdds(odds.data || odds);
        } catch (err) {
            // Handle Pera wallet user rejection gracefully
            if (err?.message?.includes('cancelled') || err?.message?.includes('rejected')) {
                toast.error('Transaction cancelled by user');
            } else {
                toast.error(err.message || 'Failed to send tip');
            }
        } finally {
            setSending(false);
        }
    };

    if (loading) return <div className="page-container"><div className="loading-center"><div className="spinner" /></div></div>;

    const appId = contract?.app_id || contract?.appId;

    return (
        <div className="page-container" style={{ maxWidth: 600, margin: '0 auto' }}>
            <div className="page-header">
                <div>
                    <h1>💸 Send Tip</h1>
                    <p className="page-subtitle">to {truncateWallet(creatorWallet)}</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <Link to={`/store/${creatorWallet}`} className="btn btn-secondary btn-sm">🛍️ Store</Link>
                    <Link to="/explore" className="btn btn-secondary btn-sm">← Back</Link>
                </div>
            </div>

            {/* Contract Info */}
            {contract ? (
                <div className="card" style={{ marginBottom: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>TipProxy Contract</div>
                            <div style={{ fontWeight: 700 }}>App ID: {appId}</div>
                            <div className="wallet-addr" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                {truncateWallet(contract.app_address || contract.appAddress)}
                            </div>
                        </div>
                        <span className={`badge ${contract.active ? 'badge-success' : 'badge-danger'}`}>
                            {contract.active ? 'Active' : 'Paused'}
                        </span>
                    </div>
                </div>
            ) : (
                <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent-red)' }}>
                    <p style={{ color: 'var(--accent-red)' }}>⚠️ Creator has no active contract</p>
                </div>
            )}

            {/* Tip Form */}
            <div className="card" style={{ marginBottom: 20 }}>
                <div className="form-group">
                    <label className="form-label">Amount (ALGO)</label>
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        min="0.1"
                        step="0.1"
                        style={{ fontSize: '1.2rem', fontWeight: 700 }}
                    />
                </div>
                <div className="form-group">
                    <label className="form-label">Memo (optional)</label>
                    <input value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="Great content!" />
                </div>
                <button
                    className="btn btn-lg btn-primary"
                    style={{ width: '100%' }}
                    onClick={handleTip}
                    disabled={sending || !appId}
                >
                    {sending ? 'Signing via Pera...' : `💸 Send ${amount} ALGO Tip`}
                </button>
                {lastTxId && (
                    <div style={{ marginTop: 10, fontSize: '0.8rem', color: 'var(--accent-cyan)', textAlign: 'center' }}>
                        ✅ Last TX: <a href={`https://testnet.explorer.perawallet.app/tx/${lastTxId}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)' }}>{truncateWallet(lastTxId)}</a>
                    </div>
                )}
            </div>

            {/* Status Cards */}
            {isAuthenticated && (
                <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr 1fr' }}>
                    {/* Loyalty */}
                    <div className="card">
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>🏆 Butki Loyalty</div>
                        {loyalty ? (
                            <>
                                <div style={{ fontWeight: 700, fontSize: '1.2rem' }}>{loyalty.butki_badges_earned || loyalty.butkiBadgesEarned || 0} badges</div>
                                <div className="progress-bar" style={{ marginTop: 8, marginBottom: 4 }}>
                                    <div className="progress-fill" style={{ width: `${((5 - (loyalty.tips_to_next_badge ?? loyalty.tipsToNextBadge ?? 5)) / 5) * 100}%` }} />
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                    {loyalty.tip_count || loyalty.tipCount || 0} tips · {loyalty.tips_to_next_badge ?? loyalty.tipsToNextBadge ?? 5} to next badge
                                </div>
                            </>
                        ) : (
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>No tips yet — start now!</div>
                        )}
                    </div>

                    {/* Membership */}
                    <div className="card">
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>🎫 Bauni Membership</div>
                        {(membership?.is_valid || membership?.isValid) ? (
                            <>
                                <span className="badge badge-success">Active</span>
                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 6 }}>
                                    {membership.days_remaining || membership.daysRemaining} days left
                                </div>
                            </>
                        ) : (
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                Not a member — tip to qualify
                            </div>
                        )}
                    </div>

                    {/* Golden Odds */}
                    <div className="card" style={{ gridColumn: 'span 2' }}>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>⭐ Golden Sticker Odds</div>
                        {goldenOdds ? (
                            <div>
                                <span style={{ fontWeight: 800, fontSize: '1.5rem', color: 'var(--accent-gold)' }}>
                                    {((goldenOdds.probability ?? goldenOdds.odds_percent ?? 0) * (goldenOdds.probability != null ? 100 : 1)).toFixed(1)}%
                                </span>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginLeft: 8 }}>
                                    chance at {amount} ALGO
                                </span>
                            </div>
                        ) : (
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Connect wallet to see odds</div>
                        )}
                    </div>
                </div>
            )}

            {/* Bottom links */}
            {isAuthenticated && (
                <div className="quick-actions" style={{ marginTop: 24, display: 'flex', gap: 8 }}>
                    <Link to="/fan" className="btn btn-secondary">📦 My Collection</Link>
                    <Link to="/explore" className="btn btn-secondary">🏆 Leaderboard</Link>
                </div>
            )}
        </div>
    );
}
