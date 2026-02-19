import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { authApi } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [wallet, setWallet] = useState(localStorage.getItem('fanforge_wallet') || null);
    const [role, setRole] = useState(localStorage.getItem('fanforge_role') || null);
    const [jwt, setJwt] = useState(localStorage.getItem('fanforge_jwt') || null);

    const isAuthenticated = !!jwt && !!wallet;
    const isCreator = role === 'creator';
    const isFan = role === 'fan' || role === 'creator'; // creators can also act as fans

    const login = useCallback(async (walletAddress, signBytes) => {
        // Step 1: Get challenge from backend
        const challenge = await authApi.createChallenge(walletAddress);
        console.log('[Auth] Challenge received:', { nonce: challenge.nonce?.slice(0, 10) + '...', hasMessage: !!challenge.message });

        // Step 2: Sign nonce with Pera Wallet
        // Pera signData signs: MX + data internally (Ed25519 domain separation)
        // Backend verify_bytes also prepends MX — so we sign raw nonce bytes
        const nonceBytes = new TextEncoder().encode(challenge.nonce);

        let signedBytes;
        try {
            signedBytes = await signBytes(nonceBytes);
            console.log('[Auth] Signature received, type:', typeof signedBytes, 'length:', signedBytes?.length || signedBytes?.byteLength);
        } catch (signErr) {
            console.error('[Auth] Pera signing failed:', signErr);
            throw new Error('Wallet signing cancelled or failed');
        }

        // Step 3: Convert signature to base64
        // signedBytes might be Uint8Array or ArrayBuffer
        let sigArray;
        if (signedBytes instanceof Uint8Array) {
            sigArray = signedBytes;
        } else if (signedBytes instanceof ArrayBuffer) {
            sigArray = new Uint8Array(signedBytes);
        } else if (Array.isArray(signedBytes)) {
            sigArray = new Uint8Array(signedBytes);
        } else {
            // May already be a base64 string
            console.log('[Auth] Unexpected signedBytes type:', typeof signedBytes, signedBytes);
            sigArray = new Uint8Array(signedBytes);
        }

        // Convert to base64 safely (handles large arrays)
        let signature;
        const chunkSize = 0x8000; // 32KB chunks to avoid call stack overflow
        const chunks = [];
        for (let i = 0; i < sigArray.length; i += chunkSize) {
            chunks.push(String.fromCharCode.apply(null, sigArray.subarray(i, i + chunkSize)));
        }
        signature = btoa(chunks.join(''));
        console.log('[Auth] Signature base64 length:', signature.length, 'first 20 chars:', signature.slice(0, 20));

        // Step 4: Verify signature with backend → get JWT
        const result = await authApi.verifySignature(walletAddress, challenge.nonce, signature);
        console.log('[Auth] Login successful! Role:', result.role || result.data?.role);

        // Step 5: Store auth state
        const accessToken = result.accessToken || result.access_token || result.data?.accessToken;
        const returnedWallet = result.walletAddress || result.wallet_address || result.data?.walletAddress || walletAddress;
        const returnedRole = result.role || result.data?.role || 'fan';

        localStorage.setItem('fanforge_jwt', accessToken);
        localStorage.setItem('fanforge_wallet', returnedWallet);
        localStorage.setItem('fanforge_role', returnedRole);

        setJwt(accessToken);
        setWallet(returnedWallet);
        setRole(returnedRole);

        return result;
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('fanforge_jwt');
        localStorage.removeItem('fanforge_wallet');
        localStorage.removeItem('fanforge_role');
        setJwt(null);
        setWallet(null);
        setRole(null);
    }, []);

    const updateRole = useCallback((newRole) => {
        localStorage.setItem('fanforge_role', newRole);
        setRole(newRole);
    }, []);

    return (
        <AuthContext.Provider value={{
            wallet, role, jwt, isAuthenticated, isCreator, isFan,
            login, logout, updateRole,
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
