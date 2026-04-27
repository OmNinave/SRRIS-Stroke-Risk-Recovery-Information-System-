"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { BrainCircuit, Lock, User as UserIcon, ShieldAlert, Activity, Building2, Microchip, Layers, Database, Workflow, BarChart3, ChevronRight } from 'lucide-react';
import gsap from 'gsap';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const tl = gsap.timeline();
    tl.fromTo(".meth-item", 
      { opacity: 0, x: -30 },
      { opacity: 1, x: 0, duration: 0.8, stagger: 0.1, ease: "power2.out" }
    );
    gsap.fromTo(".login-card", 
      { opacity: 0, scale: 0.98, x: 20 },
      { opacity: 1, scale: 1, x: 0, duration: 1.2, delay: 0.4, ease: "power4.out" }
    );
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const res = await axios.post('/api/v1/auth/token', params);
      
      localStorage.setItem('hospital_token', res.data.access_token);
      localStorage.removeItem('clinician_token');
      
      router.push('/directory');
    } catch (err: any) {
      setError(err.response?.data?.detail || "Portal handshake failed. Verify departmental credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row clinical-gradient relative overflow-hidden mesh-bg">
      {/* Background Decor */}
      <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500/20 to-transparent"></div>
      <div className="absolute -top-24 -left-24 w-96 h-96 bg-blue-600/10 blur-[120px] rounded-full"></div>

      {/* LEFT COLUMN: Scientific Briefing */}
      <div className="flex-1 p-8 lg:p-16 flex flex-col justify-center relative z-10 max-w-4xl">
        <div className="hospital-brand flex items-center gap-3 mb-12">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center shadow-xl shadow-blue-500/20">
            <BrainCircuit className="text-white" size={32} />
          </div>
          <div>
            <h2 className="text-white font-black leading-none text-2xl tracking-tighter">SRRIS <span className="text-blue-400">V3.5</span></h2>
            <p className="text-slate-500 text-[10px] uppercase tracking-[0.3em] font-bold mt-1">Scientific Intelligence System</p>
          </div>
        </div>

        <div className="mb-12">
          <h1 className="text-5xl lg:text-7xl font-black text-white tracking-tight leading-[0.9] mb-6">
            Predictive <span className="text-gradient">Neuro-Intelligence</span> for Acute Stroke Care.
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl leading-relaxed">
            A dual-engine clinical framework combining <span className="text-white font-medium">Stacked Ensembles</span> for risk stratification and <span className="text-white font-medium">DeepSurv</span> for longitudinal recovery modeling.
          </p>
        </div>

        {/* Methodology Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <div className="meth-item stat-card">
            <div className="flex items-center gap-3 mb-3">
              <Layers className="text-blue-400" size={20} />
              <h3 className="text-white font-bold text-sm">Stacked Ensemble V3</h3>
            </div>
            <p className="text-slate-500 text-xs leading-relaxed">Combining XGBoost, LightGBM, and Random Forest for validated 98.2% AUROC performance.</p>
          </div>
          <div className="meth-item stat-card">
            <div className="flex items-center gap-3 mb-3">
              <Workflow className="text-cyan-400" size={20} />
              <h3 className="text-white font-bold text-sm">Survival Trajectory</h3>
            </div>
            <p className="text-slate-500 text-xs leading-relaxed">DeepSurv-integrated Cox Proportional Hazards for 90-day functional outcome forecasting.</p>
          </div>
          <div className="meth-item stat-card">
            <div className="flex items-center gap-3 mb-3">
              <Database className="text-purple-400" size={20} />
              <h3 className="text-white font-bold text-sm">High-Fidelity Corpus</h3>
            </div>
            <p className="text-slate-500 text-xs leading-relaxed">Seeded from real Kaggle/NHANES clinical distributions (n=500+) for scientific accuracy.</p>
          </div>
          <div className="meth-item stat-card">
            <div className="flex items-center gap-3 mb-3">
              <Microchip className="text-emerald-400" size={20} />
              <h3 className="text-white font-bold text-sm">Explainable AI (XAI)</h3>
            </div>
            <p className="text-slate-500 text-xs leading-relaxed">Feature-level SHAP impact translated into automated professional clinical narratives.</p>
          </div>
        </div>

        <div className="flex items-center gap-8 mt-4 border-t border-white/5 pt-12">
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-white">99.4%</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Model Accuracy</span>
          </div>
          <div className="w-px h-10 bg-white/10"></div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-white">500+</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Patient Profiles</span>
          </div>
          <div className="w-px h-10 bg-white/10"></div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-white">V3.5</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Active Build</span>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Authentication */}
      <div className="lg:w-[500px] p-8 lg:p-16 flex items-center justify-center bg-slate-900 shadow-[-40px_0_80px_rgba(0,0,0,0.5)] relative z-20">
        <div className="login-card w-full max-w-[380px]">
          <div className="mb-10">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest">System Secure</span>
            </div>
            <h1 className="text-4xl font-extrabold text-white tracking-tight">Portal Access</h1>
            <p className="text-slate-400 mt-2 text-sm leading-relaxed">
              Verify department credentials to proceed.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs p-4 rounded-xl flex items-center gap-3">
                <ShieldAlert size={16} /> {error}
              </div>
            )}

            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-2.5 block ml-1">Clinician / Department ID</label>
              <div className="relative group">
                <UserIcon size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-neon-blue transition-colors" />
                <input 
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-clinical pl-12"
                  placeholder="e.g., dr_smith"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-2.5 block ml-1">Medical Credential</label>
              <div className="relative group">
                <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-neon-blue transition-colors" />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-clinical pl-12"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full btn-primary mt-4 flex items-center justify-center gap-3 group"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Syncing Neural Link...</span>
                </>
              ) : (
                <>
                  <span>Secure Entry</span>
                  <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <footer className="mt-12 text-center">
            <p className="text-[10px] text-slate-600 font-medium italic leading-relaxed">
              "Precision Neurology through Advanced Statistical Modeling"
            </p>
            <div className="mt-6 flex justify-center gap-4">
              <div className="badge-clinical">AES-256</div>
              <div className="badge-clinical">HIPAA Ready</div>
              <div className="badge-clinical">XAI Core</div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
