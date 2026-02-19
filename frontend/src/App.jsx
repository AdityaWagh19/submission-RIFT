import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WalletProvider } from './context/WalletContext';
import { ToastProvider } from './context/ToastContext';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import CreatorHub from './pages/CreatorHub';
import FanHub from './pages/FanHub';
import Store from './pages/Store';
import Explore from './pages/Explore';
import Tip from './pages/Tip';

export default function App() {
  return (
    <BrowserRouter>
      <WalletProvider>
        <AuthProvider>
          <ToastProvider>
            <div className="app-layout">
              <Navbar />
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/creator" element={<CreatorHub />} />
                <Route path="/fan" element={<FanHub />} />
                <Route path="/store/:creatorWallet" element={<Store />} />
                <Route path="/explore" element={<Explore />} />
                <Route path="/tip/:creatorWallet" element={<Tip />} />
              </Routes>
            </div>
          </ToastProvider>
        </AuthProvider>
      </WalletProvider>
    </BrowserRouter>
  );
}
