"use client";

import { useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { BrainCircuit, Lock, User as UserIcon, ShieldAlert } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Must use URLSearchParams for x-www-form-urlencoded OAuth2 specs
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const res = await axios.post('/api/v1/auth/token', params);
      
      // Store JWT Token Securely
      localStorage.setItem('hospital_token', res.data.access_token);
      
      // Redirect to the Secure Directory
      router.push('/directory');
    } catch (err: any) {
      setError(err.response?.data?.detail || "System rejected credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 clinical-gradient">
      <div className="glass-panel p-10 w-full max-w-md relative overflow-hidden">
        {/* Decorative Grid */}
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-10 pointer-events-none"></div>
        
        <div className="text-center mb-8 relative z-10">
          <div className="inline-flex w-16 h-16 rounded-full bg-slate-900 border border-[var(--color-neon-blue)] items-center justify-center mb-4 shadow-[0_0_15px_rgba(0,240,255,0.4)]">
            <ShieldAlert size={32} className="text-[var(--color-neon-blue)]" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">SRRIS Secure Access</h1>
          <p className="text-slate-400 text-sm mt-2">Clinical Decision Support V3.0</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6 relative z-10">
          {error && (
            <div className="bg-red-900/40 border border-red-500/50 text-red-300 text-sm p-3 rounded text-center">
              {error}
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2 block">Clinician ID / Username</label>
            <div className="relative">
              <UserIcon size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input 
                type="text" 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900/60 border border-slate-700 rounded-lg py-3 pl-10 pr-4 text-white focus:outline-none focus:border-[var(--color-neon-blue)] transition-colors"
                placeholder="e.g. dr_smith"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2 block">Security Credential</label>
            <div className="relative">
              <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900/60 border border-slate-700 rounded-lg py-3 pl-10 pr-4 text-white focus:outline-none focus:border-[var(--color-neon-blue)] transition-colors"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3.5 bg-blue-600 hover:bg-blue-500 bg-opacity-90 rounded-lg text-white font-bold transition-all disabled:opacity-50"
          >
            {loading ? 'Authenticating Identity...' : 'Access Database Terminal'}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-700/50 text-center">
          <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
            <BrainCircuit size={12} /> Encrypted via AES-256 JWT Subsystems
          </p>
        </div>
      </div>
    </div>
  );
}
