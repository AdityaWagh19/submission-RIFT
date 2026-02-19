import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useWallet } from '../context/WalletContext';

export default function Navbar() {
    const { wallet, role, isAuthenticated, logout } = useAuth();
    const { disconnect } = useWallet();
    const location = useLocation();

    const truncate = (addr) => addr ? `${addr.slice(0, 4)}...${addr.slice(-4)}` : '';
    const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

    const handleDisconnect = () => {
        logout();
        disconnect();
    };

    return (
        <nav className="navbar">
            <Link to="/" className="navbar-brand">
                <span className="brand-icon">🌟</span>
                FanForge
            </Link>

            <div className="navbar-links">
                <Link to="/explore" className={`nav-link ${isActive('/explore') ? 'active' : ''}`}>
                    Explore
                </Link>

                {isAuthenticated && role === 'creator' && (
                    <Link to="/creator" className={`nav-link ${isActive('/creator') ? 'active' : ''}`}>
                        Creator Hub
                    </Link>
                )}

                {isAuthenticated && (
                    <Link to="/fan" className={`nav-link ${isActive('/fan') ? 'active' : ''}`}>
                        My Collection
                    </Link>
                )}
            </div>

            <div className="navbar-wallet">
                {isAuthenticated ? (
                    <>
                        {role && <span className={`role-pill ${role}`}>{role}</span>}
                        <div className="wallet-badge">
                            <span className="wallet-dot" />
                            <span className="wallet-addr">{truncate(wallet)}</span>
                        </div>
                        <button className="btn btn-sm btn-secondary" onClick={handleDisconnect}>
                            Disconnect
                        </button>
                    </>
                ) : (
                    <Link to="/" className="btn btn-sm btn-primary">
                        Connect Wallet
                    </Link>
                )}
            </div>
        </nav>
    );
}
