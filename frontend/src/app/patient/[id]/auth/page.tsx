"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter, useParams } from 'next/navigation';
import { ShieldCheck, Lock, User as UserIcon, ShieldAlert, ArrowLeft, Activity, Fingerprint, BrainCircuit } from 'lucide-react';
import gsap from 'gsap';
import Link from 'next/link';

export default function ClinicianAuthPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [patientName, setPatientName] = useState('Loading Secure Dossier...');
  const router = useRouter();
  const { id } = useParams();

  useEffect(() => {
    const hospitalToken = localStorage.getItem('hospital_token');
    if (!hospitalToken) {
      router.push('/');
      return;
    }

    const fetchPatient = async () => {
      try {
        const res = await axios.get(`/api/v1/patients/${id}`, {
          headers: { Authorization: `Bearer ${hospitalToken}` }
        });
        setPatientName(res.data.full_name);
      } catch (err) {
        setPatientName('Patient Record');
      }
    };
    fetchPatient();

    gsap.fromTo(".auth-card", 
      { opacity: 0, y: 20, scale: 0.98 },
      { opacity: 1, y: 0, scale: 1, duration: 1, ease: "power3.out" }
    );
  }, [id, router]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const res = await axios.post('/api/v1/auth/token', params);
      
      localStorage.setItem('clinician_token', res.data.access_token);
      router.push(`/patient/${id}/reports`);
    } catch (err: any) {
      setError("Clinician identity rejected. Verify credentials for record access.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 clinical-gradient relative overflow-hidden mesh-bg">
      <Link href="/directory" className="absolute top-10 left-10 flex items-center gap-2 text-slate-500 hover:text-white transition-all text-[10px] font-black uppercase tracking-[0.3em] z-20">
        <ArrowLeft size={16} /> Clinical Registry
      </Link>

      <div className="auth-card glass-panel p-12 w-full max-w-[480px] relative z-10 border-white/10 ring-1 ring-white/5 shadow-[0_0_100px_rgba(37,99,235,0.1)]">
        <div className="flex items-center gap-4 mb-10 pb-10 border-b border-white/5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/20">
            <Fingerprint size={32} />
          </div>
          <div>
            <h2 className="text-white font-black text-xl leading-none uppercase tracking-tighter">Identity Handshake</h2>
            <p className="text-blue-400 text-[10px] font-black uppercase tracking-[0.3em] mt-1">Multi-Stage Verification</p>
          </div>
        </div>

        <div className="mb-10 p-6 bg-slate-950/50 border border-white/5 rounded-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-3 opacity-20"><BrainCircuit size={40} /></div>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2 block">Restricted Access Dossier</span>
          <p className="text-white font-black text-lg tracking-tight mb-2">{patientName}</p>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
            <span className="text-[10px] text-blue-400 font-mono font-bold uppercase tracking-widest">{id}</span>
          </div>
        </div>

        <div className="mb-10">
          <h1 className="text-3xl font-black text-white tracking-tighter leading-none mb-3">Clinician Verification</h1>
          <p className="text-slate-500 text-sm leading-relaxed">
            Individual credentials are required to decrypt and synthesize clinical trajectories for this patient profile.
          </p>
        </div>

        <form onSubmit={handleVerify} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs p-5 rounded-2xl flex items-center gap-3 animate-in shake duration-500">
              <ShieldAlert size={18} /> {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em] mb-2.5 block ml-1">Clinician ID</label>
              <div className="relative group">
                <UserIcon size={18} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                <input 
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-clinical pl-14 h-16 rounded-[20px]"
                  placeholder="ID Number"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em] mb-2.5 block ml-1">Biometric / Security Key</label>
              <div className="relative group">
                <Lock size={18} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-clinical pl-14 h-16 rounded-[20px]"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full btn-primary h-16 rounded-[20px] flex items-center justify-center gap-4 shadow-xl"
          >
            {loading ? (
              <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <>
                <ShieldCheck size={24} />
                <span className="text-lg font-black tracking-tight">Access Secure Stream</span>
              </>
            )}
          </button>
        </form>

        <footer className="mt-12 pt-8 border-t border-white/5 flex flex-col items-center gap-4">
           <div className="flex items-center gap-6">
             <div className="flex items-center gap-2 text-[10px] text-slate-600 font-bold uppercase tracking-widest">
               <Activity size={12} className="text-blue-500/50" /> Audited
             </div>
             <div className="flex items-center gap-2 text-[10px] text-slate-600 font-bold uppercase tracking-widest">
               <Lock size={12} className="text-blue-500/50" /> AES-256
             </div>
           </div>
        </footer>
      </div>
    </div>
  );
}
