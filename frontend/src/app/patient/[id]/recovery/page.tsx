'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Activity, Heart, Brain, TrendingUp, AlertTriangle,
  CheckCircle, Pill, ChevronDown, ChevronUp, RefreshCw, Zap,
  Target, Clock, User, Shield, Info, Activity as ActivityIcon
} from 'lucide-react';
import { fetchRecoveryAnalysis, fetchRecoveryTrajectory, simulateRecoveryIntervention } from '@/services/api';
import { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';

/* ── Deprecated SVG Chart (Removed) ── */
/* ── circular gauge ──────────────────────────────────────── */
function Gauge({ value, color, label, size = 100 }: { value: number; color: string; label: string; size?: number }) {
  const r = size * 0.38, cx = size / 2, cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (value / 100) * circumference;
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: 'stroke-dashoffset 1.2s ease' }} />
        <text x={cx} y={cy + 5} textAnchor="middle" fontSize={size * 0.18} fontWeight="800" fill="#0f172a">{value}%</text>
      </svg>
      <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 text-center">{label}</span>
    </div>
  );
}

/* ── bar indicator ───────────────────────────────────────── */
function RiskBar({ label, value, color, bg }: { label: string; value: number; color: string; bg: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{label}</span>
        <span className={`text-xs font-black ${color}`}>{value}%</span>
      </div>
      <div className="w-full h-2 rounded-full" style={{ background: bg }}>
        <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${value}%`, background: color.replace('text-', '') }} />
      </div>
    </div>
  );
}

const PRIORITY_COLORS: Record<string, string> = {
  URGENT: 'bg-red-500',
  IMMEDIATE: 'bg-orange-500',
  'SHORT-TERM': 'bg-blue-500',
  CONSIDER: 'bg-slate-400',
};

export default function RecoveryPage() {
  const { id: uid } = useParams() as { id: string };
  const router = useRouter();

  const [data, setData] = useState<any>(null);
  const [trajectory, setTrajectory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedMed, setExpandedMed] = useState<number | null>(null);

  // What-If simulation state
  const [simBP, setSimBP] = useState(130);
  const [simAdherence, setSimAdherence] = useState(1.0);
  const [simRehab, setSimRehab] = useState(0.5);
  const [simSleep, setSimSleep] = useState(0.5);
  const [simResult, setSimResult] = useState<any>(null);
  const [simLoading, setSimLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [analysis, traj] = await Promise.all([
        fetchRecoveryAnalysis(uid),
        fetchRecoveryTrajectory(uid),
      ]);
      setData(analysis);
      setTrajectory(traj.trajectory || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load recovery data');
    } finally {
      setLoading(false);
    }
  }, [uid]);

  useEffect(() => { load(); }, [load]);

  const runSim = async () => {
    setSimLoading(true);
    try {
      const res = await simulateRecoveryIntervention(uid, {
        systolic_bp: simBP,
        medication_adherence_score: simAdherence,
        rehab_hours_per_day: simRehab,
        sleep_quality_score: simSleep
      });
      setSimResult(res);
    } catch (e: any) {
      alert('Simulation error: ' + e.message);
    } finally {
      setSimLoading(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-4 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin" />
        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Loading Recovery Intelligence...</span>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center p-8 bg-white rounded-2xl border border-red-100 shadow">
        <AlertTriangle className="mx-auto text-red-500 mb-3" size={32} />
        <p className="font-bold text-slate-700 mb-2">Recovery Engine Error</p>
        <p className="text-sm text-slate-500 mb-4">{error}</p>
        <button onClick={load} className="bg-indigo-600 text-white px-5 py-2 rounded-xl text-sm font-bold hover:bg-indigo-700">Retry</button>
      </div>
    </div>
  );

  const outcomeColor = data?.outcome_category === 'GOOD' ? '#10b981' : data?.outcome_category === 'MODERATE' ? '#f59e0b' : '#ef4444';
  const detAlertColor = (data?.deterioration_risk_72h ?? 0) >= 25 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200';
  const detTextColor = (data?.deterioration_risk_72h ?? 0) >= 25 ? 'text-red-600' : 'text-green-600';

  // Merge trajectory for Twin-Path chart
  const chartData = trajectory.map(basePoint => {
    const simPoint = simResult?.simulated?.trajectory?.find((p: any) => p.day === basePoint.day);
    return {
      day: basePoint.day,
      baseline: basePoint.recovery_probability,
      simulated: simPoint ? simPoint.recovery_probability : null,
      milestone: basePoint.milestone
    };
  });

  return (
    <div className="bg-slate-50 min-h-screen pb-20">
      {/* Nav */}
      <nav className="max-w-7xl mx-auto px-4 md:px-8 pt-8 mb-8 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/patient/${uid}`} className="flex items-center gap-2 text-slate-500 hover:text-slate-900 font-bold transition-colors">
            <ArrowLeft size={18} /> Patient Overview
          </Link>
          <span className="text-slate-300">|</span>
          <span className="text-[10px] font-black uppercase tracking-widest text-indigo-600 flex items-center gap-1.5">
            <Brain size={12} /> Recovery Intelligence
          </span>
        </div>
        <button onClick={load} className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-2 rounded-xl text-sm font-bold hover:bg-slate-50 transition-colors">
          <RefreshCw size={14} /> Refresh
        </button>
      </nav>

      <div className="max-w-7xl mx-auto px-4 md:px-8 grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Clinical Summary Banner ── */}
        <div className="lg:col-span-3 bg-[#0a0f1d] rounded-3xl p-6 border border-white/5 text-white">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 flex items-center justify-center shrink-0">
              <Brain size={20} className="text-indigo-400" />
            </div>
            <div className="flex-1">
              <p className="text-[10px] font-black uppercase tracking-widest text-indigo-400 mb-2">
                OPSUM-Inspired Recovery Engine · Klug et al. Nature Comms Med 2024
              </p>
              <p className="text-sm text-slate-300 leading-relaxed">
                {(data?.clinical_summary || '').split('**').map((part: string, i: number) => 
                  i % 2 === 1 ? <strong key={i} className="text-white">{part}</strong> : part
                )}
              </p>
            </div>
            {data?.deterioration_alert && (
              <div className="shrink-0 bg-red-500/10 border border-red-500/30 px-4 py-2 rounded-xl flex items-center gap-2">
                <AlertTriangle size={16} className="text-red-400 animate-pulse" />
                <span className="text-[10px] font-black uppercase tracking-widest text-red-400">72h Alert</span>
              </div>
            )}
          </div>
        </div>

        {/* ── Recovery Gauges ── */}
        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
            <Target size={12} /> Functional Outcome Prediction
          </h3>
          <div className="flex justify-around flex-wrap gap-4 mb-6">
            <Gauge value={data?.good_recovery_probability ?? 0} color={outcomeColor} label="Good Recovery (mRS ≤ 2)" size={110} />
            <Gauge value={data?.gait_recovery_probability ?? 0} color="#6366f1" label="Gait / Motor Recovery" size={110} />
          </div>
          <div className={`rounded-2xl border p-4 ${data?.outcome_category === 'GOOD' ? 'bg-green-50 border-green-200' : data?.outcome_category === 'MODERATE' ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">Expected mRS at 90 Days</div>
            <div className="text-2xl font-black text-slate-900">{data?.expected_mrs_score ?? '—'}</div>
            <div className="text-xs font-bold text-slate-600 mt-0.5">{data?.mrs_label}</div>
          </div>
          <div className="mt-4 text-[9px] font-black uppercase text-slate-400 text-center tracking-widest">
            CI: {data?.recovery_confidence_interval?.lower}% – {data?.recovery_confidence_interval?.upper}%
          </div>
        </div>

        {/* ── Risk Bars ── */}
        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
            <Shield size={12} /> Clinical Risk Profile
          </h3>
          <div className="space-y-5 mb-6">
            <div>
              <div className="flex justify-between mb-1.5">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Hospital Mortality Risk</span>
                <span className="text-xs font-black text-red-500">{data?.hospital_mortality_risk ?? 0}%</span>
              </div>
              <div className="w-full h-2 bg-red-50 rounded-full">
                <div className="h-full bg-red-400 rounded-full transition-all duration-1000" style={{ width: `${data?.hospital_mortality_risk ?? 0}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1.5">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">90-Day Mortality Risk</span>
                <span className="text-xs font-black text-orange-500">{data?.mortality_90day_risk ?? 0}%</span>
              </div>
              <div className="w-full h-2 bg-orange-50 rounded-full">
                <div className="h-full bg-orange-400 rounded-full transition-all duration-1000" style={{ width: `${data?.mortality_90day_risk ?? 0}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1.5">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Gait Recovery</span>
                <span className="text-xs font-black text-indigo-600">{data?.gait_recovery_probability ?? 0}%</span>
              </div>
              <div className="w-full h-2 bg-indigo-50 rounded-full">
                <div className="h-full bg-indigo-500 rounded-full transition-all duration-1000" style={{ width: `${data?.gait_recovery_probability ?? 0}%` }} />
              </div>
            </div>
          </div>

          {/* 72h deterioration alert */}
          <div className={`rounded-2xl border p-4 ${detAlertColor}`}>
            <div className="flex items-center gap-2 mb-1">
              {(data?.deterioration_risk_72h ?? 0) >= 25
                ? <AlertTriangle size={14} className="text-red-500 animate-pulse" />
                : <CheckCircle size={14} className="text-green-500" />}
              <span className={`text-[10px] font-black uppercase tracking-widest ${detTextColor}`}>
                72h Deterioration Risk: {data?.deterioration_risk_72h ?? 0}%
              </span>
            </div>
            <p className="text-[10px] text-slate-600 leading-relaxed">{data?.monitoring_recommendation}</p>
          </div>
        </div>

        {/* ── Physiotherapy & Walk ── */}
        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm flex flex-col justify-between">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
            <Activity size={12} /> Motor Rehabilitation Plan
          </h3>
          <div className="flex-1 flex flex-col gap-4">
            <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-4">
              <div className="text-[10px] font-black uppercase text-indigo-500 tracking-widest mb-2 flex items-center gap-1.5"><Clock size={10} />Walk Timeline</div>
              <p className="text-sm font-bold text-indigo-900">{data?.weeks_to_walk}</p>
            </div>
            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4">
              <div className="text-[10px] font-black uppercase text-slate-400 tracking-widest mb-2">PT Intensity</div>
              <p className="text-sm font-bold text-slate-700">{data?.physiotherapy_intensity}</p>
            </div>
            <div className={`rounded-2xl p-4 border ${data?.orthotics_needed ? 'bg-orange-50 border-orange-200' : 'bg-green-50 border-green-200'}`}>
              <div className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: data?.orthotics_needed ? '#ea580c' : '#16a34a' }}>
                Orthotics / Assistive Device
              </div>
              <p className="text-sm font-bold" style={{ color: data?.orthotics_needed ? '#9a3412' : '#14532d' }}>
                {data?.orthotics_needed ? 'Assessment Recommended' : 'Not Required at This Stage'}
              </p>
            </div>
          </div>
        </div>

        {/* ── 90-Day Trajectory Chart (Interactive Twin-Path) ── */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <TrendingUp size={12} /> 90-Day Recovery Trajectory
            </h3>
            <div className="flex gap-2">
              <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 bg-slate-50 px-2 py-1 rounded-lg flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-slate-400" /> Baseline</span>
              {simResult && <span className="text-[9px] font-black uppercase tracking-widest text-indigo-500 bg-indigo-50 px-2 py-1 rounded-lg flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-indigo-500" /> Optimized Path</span>}
            </div>
          </div>
          
          <div className="w-full h-[220px]">
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorBaseline" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorSim" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="day" tickFormatter={(val) => `D${val}`} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94a3b8', fontWeight: 700 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94a3b8', fontWeight: 700 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip 
                  contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '11px', fontWeight: 'bold' }}
                  labelStyle={{ color: '#64748b', marginBottom: '4px' }}
                  formatter={(value: any) => [`${value}%`, 'Recovery Prob']}
                  labelFormatter={(label) => `Day ${label}`}
                />
                <Area type="monotone" dataKey="baseline" stroke="#94a3b8" strokeWidth={2} fillOpacity={1} fill="url(#colorBaseline)" isAnimationActive={true} />
                {simResult && <Area type="monotone" dataKey="simulated" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorSim)" isAnimationActive={true} />}
                
                {chartData.filter(d => d.milestone).map((d, i) => (
                  <ReferenceDot key={i} x={d.day} y={simResult ? d.simulated : d.baseline} r={4} fill={simResult ? "#6366f1" : "#94a3b8"} stroke="none" />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          
          <div className="mt-4 grid grid-cols-3 gap-3">
            {chartData.filter(p => p.milestone).slice(0, 3).map((p, i) => (
              <div key={i} className="bg-slate-50 border border-slate-100 rounded-xl p-3">
                <div className="text-indigo-600 font-black text-xs mb-0.5">Day {p.day}</div>
                <div className="text-[10px] text-slate-600 font-medium">{p.milestone}</div>
                <div className="text-[10px] text-slate-400 mt-1">{p.baseline}% baseline</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Medication Protocol ── */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <Pill size={12} /> Medication Protocol ({data?.medication_plan?.length ?? 0})
          </h3>
          <div className="space-y-2 overflow-y-auto" style={{ maxHeight: 340 }}>
            {(data?.medication_plan ?? []).map((med: any, i: number) => (
              <div key={i} className="border border-slate-100 rounded-2xl overflow-hidden">
                <button
                  onClick={() => setExpandedMed(expandedMed === i ? null : i)}
                  className="w-full p-3 text-left flex items-center gap-3 hover:bg-slate-50 transition-colors"
                >
                  <span className={`${PRIORITY_COLORS[med.priority] ?? 'bg-slate-400'} text-white text-[8px] font-black uppercase px-2 py-0.5 rounded-full shrink-0`}>
                    {med.priority}
                  </span>
                  <span className="text-xs font-bold text-slate-700 flex-1 text-left line-clamp-1">{med.drug}</span>
                  {expandedMed === i ? <ChevronUp size={14} className="text-slate-400 shrink-0" /> : <ChevronDown size={14} className="text-slate-400 shrink-0" />}
                </button>
                {expandedMed === i && (
                  <div className="px-3 pb-3 space-y-2">
                    <p className="text-[10px] text-slate-500 font-medium leading-relaxed">{med.indication}</p>
                    <p className="text-[9px] text-indigo-500 font-black uppercase tracking-widest">Evidence: {med.evidence}</p>
                    <p className="text-[9px] text-slate-400 uppercase tracking-widest">{med.phase}</p>
                    {med.interaction_warning && (
                      <div className="mt-2 bg-red-50 border border-red-200 text-red-600 text-[9px] font-bold p-2 rounded-lg flex items-start gap-1.5 leading-relaxed">
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        <span>{med.interaction_warning}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── What-If Simulation ── */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <Zap size={12} /> Causal AI Sandbox — What-If Simulation
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 block mb-2">
                Target Systolic BP: <strong className="text-slate-900">{simBP} mmHg</strong>
              </label>
              <input type="range" min="100" max="200" value={simBP} onChange={e => setSimBP(Number(e.target.value))}
                className="w-full accent-indigo-600" />
              <div className="flex justify-between text-[9px] text-slate-400 font-bold mt-1"><span>100</span><span>200</span></div>
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 block mb-2">
                Medication Adherence: <strong className="text-slate-900">{Math.round(simAdherence * 100)}%</strong>
              </label>
              <input type="range" min="0" max="1" step="0.05" value={simAdherence} onChange={e => setSimAdherence(Number(e.target.value))}
                className="w-full accent-indigo-600" />
              <div className="flex justify-between text-[9px] text-slate-400 font-bold mt-1"><span>0%</span><span>100%</span></div>
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 block mb-2">
                Rehab PT Hours: <strong className="text-slate-900">{simRehab.toFixed(1)} hrs/day</strong>
              </label>
              <input type="range" min="0" max="3" step="0.5" value={simRehab} onChange={e => setSimRehab(Number(e.target.value))}
                className="w-full accent-indigo-600" />
              <div className="flex justify-between text-[9px] text-slate-400 font-bold mt-1"><span>0h</span><span>3h</span></div>
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 block mb-2">
                Sleep Quality Score: <strong className="text-slate-900">{Math.round(simSleep * 100)}%</strong>
              </label>
              <input type="range" min="0" max="1" step="0.1" value={simSleep} onChange={e => setSimSleep(Number(e.target.value))}
                className="w-full accent-indigo-600" />
              <div className="flex justify-between text-[9px] text-slate-400 font-bold mt-1"><span>Poor</span><span>Optimum</span></div>
            </div>
          </div>
          <button onClick={runSim} disabled={simLoading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 transition-colors mb-4">
            {simLoading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Zap size={14} />}
            Run Simulation
          </button>
          {simResult && (
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Recovery', baseline: simResult.baseline.good_recovery_probability, sim: simResult.simulated.good_recovery_probability, delta: simResult.deltas.recovery_change, good: simResult.deltas.recovery_change >= 0 },
                { label: 'Gait', baseline: simResult.baseline.gait_recovery_probability, sim: simResult.simulated.gait_recovery_probability, delta: simResult.deltas.gait_change, good: simResult.deltas.gait_change >= 0 },
                { label: 'Mortality', baseline: simResult.baseline.hospital_mortality_risk, sim: simResult.simulated.hospital_mortality_risk, delta: simResult.deltas.mortality_change, good: simResult.deltas.mortality_change <= 0 },
              ].map((item, i) => (
                <div key={i} className={`rounded-2xl border p-4 ${item.good ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">{item.label}</div>
                  <div className="text-xs text-slate-500">{item.baseline}% → <span className="font-black text-slate-900">{item.sim}%</span></div>
                  <div className={`text-lg font-black mt-1 ${item.good ? 'text-green-600' : 'text-red-600'}`}>
                    {item.delta >= 0 ? '+' : ''}{item.delta}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Dual-Engine AI Comparison Panel ── */}
        <div className="lg:col-span-3 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <Brain size={12} /> Dual-Engine AI Comparison
            </h3>
          </div>
          
          <p className="text-xs text-slate-500 mb-6 max-w-3xl">
            Two independent machine learning models analyzing the same patient profile. Comparing their outputs helps validate clinical decisions and flag hidden discrepancies.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Engine 1: Recovery Outcome Model (mRS) */}
            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500"></div>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Engine 1 — Recovery Outcome ML</span>
              </div>
              <p className="text-xs text-slate-600 mb-5 leading-relaxed">
                <strong className="text-slate-900">Architecture:</strong> StackingClassifier (RF+GBM+LR)<br/>
                <strong className="text-slate-900">Cohort:</strong> 102,135 patients (Josline90 / Swedish Riksstroke Registry)<br/>
                <strong className="text-slate-900">Accuracy:</strong> {data?.recovery_outcome_ml?.cv_accuracy ?? 'N/A'}% CV
              </p>
              
              {data?.recovery_outcome_ml?.available ? (
                <>
                  <div className={`rounded-xl border p-4 mb-5 ${
                    data.recovery_outcome_ml.predicted_class === 0 ? 'bg-emerald-50 border-emerald-200' :
                    data.recovery_outcome_ml.predicted_class === 1 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">Predicted 90-Day mRS</div>
                    <div className={`text-xl font-black ${
                      data.recovery_outcome_ml.predicted_class === 0 ? 'text-emerald-700' :
                      data.recovery_outcome_ml.predicted_class === 1 ? 'text-amber-700' : 'text-red-700'
                    }`}>{data.recovery_outcome_ml.predicted_label}</div>
                  </div>
                  <div className="space-y-3">
                    {[
                      { label: 'Independent (mRS 0-2)', val: data.recovery_outcome_ml.probability_independent, color: 'bg-emerald-500', text: 'text-emerald-600' },
                      { label: 'Dependent (mRS 3-5)', val: data.recovery_outcome_ml.probability_dependent, color: 'bg-amber-500', text: 'text-amber-600' },
                      { label: 'Dead (mRS 6)', val: data.recovery_outcome_ml.probability_dead, color: 'bg-red-500', text: 'text-red-600' },
                    ].map((item, i) => (
                      <div key={i}>
                        <div className="flex justify-between mb-1">
                          <span className="text-xs font-bold text-slate-700">{item.label}</span>
                          <span className={`text-xs font-black ${item.text}`}>{item.val}%</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-200">
                          <div className={`h-full rounded-full transition-all duration-700 ${item.color}`} style={{ width: `${item.val}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-sm text-slate-400 font-medium">Model unavailable</div>
              )}
            </div>

            {/* Engine 2: STROKEPREDICTENGINE RF */}
            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-violet-500"></div>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Engine 2 — STROKEPREDICTENGINE RF</span>
              </div>
              <p className="text-xs text-slate-600 mb-5 leading-relaxed">
                <strong className="text-slate-900">Architecture:</strong> RandomForestClassifier (100 Trees)<br/>
                <strong className="text-slate-900">Cohort:</strong> Multi-Modal Clinical EHR Dataset<br/>
                <strong className="text-slate-900">Accuracy:</strong> {data?.secondary_opinion?.accuracy ?? 'N/A'}
              </p>
              
              {data?.secondary_opinion?.available ? (
                <>
                  <div className={`rounded-xl border p-4 mb-5 ${
                    data.secondary_opinion.risk_tier === 'LOW' ? 'bg-emerald-50 border-emerald-200' :
                    data.secondary_opinion.risk_tier === 'MODERATE' ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">Stroke Risk Probability</div>
                    <div className="flex items-end gap-3">
                      <div className={`text-3xl font-black ${
                        data.secondary_opinion.risk_tier === 'LOW' ? 'text-emerald-700' :
                        data.secondary_opinion.risk_tier === 'MODERATE' ? 'text-amber-700' : 'text-red-700'
                      }`}>{data.secondary_opinion.stroke_risk_probability}%</div>
                      <div className={`text-xs font-black uppercase tracking-widest mb-1.5 ${
                        data.secondary_opinion.risk_tier === 'LOW' ? 'text-emerald-600' :
                        data.secondary_opinion.risk_tier === 'MODERATE' ? 'text-amber-600' : 'text-red-600'
                      }`}>{data.secondary_opinion.risk_tier} RISK</div>
                    </div>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2 mt-auto">
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${data.secondary_opinion.stroke_risk_probability}%`,
                        background: data.secondary_opinion.risk_tier === 'LOW' ? '#10b981' : data.secondary_opinion.risk_tier === 'MODERATE' ? '#f59e0b' : '#ef4444'
                      }} />
                  </div>
                </>
              ) : (
                <div className="text-sm text-slate-400 font-medium">Model unavailable</div>
              )}
            </div>
          </div>

          {/* Dynamic Final Verdict */}
          {data?.recovery_outcome_ml?.available && data?.secondary_opinion?.available && (
            <div className="bg-slate-900 rounded-2xl p-6 text-white shadow-md">
              <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3 flex items-center gap-2">
                <CheckCircle size={14} className="text-indigo-400" /> AI Consensus Verdict
              </h4>
              <p className="text-sm md:text-base leading-relaxed font-medium">
                {data.recovery_outcome_ml.predicted_class === 0 && data.secondary_opinion.risk_tier === 'LOW' ? (
                  <span className="text-emerald-300">✅ <strong>High Confidence:</strong> Both independent engines agree. The patient shows a low acute risk profile and a high probability of achieving functional independence (mRS 0-2). A standard rehabilitation and secondary prevention pathway is highly recommended.</span>
                ) : data.recovery_outcome_ml.predicted_class >= 1 && data.secondary_opinion.risk_tier === 'HIGH' ? (
                  <span className="text-red-300">🚨 <strong>High Risk Consensus:</strong> Both engines indicate a severe clinical trajectory. High acute stroke risk aligns with a poor expected functional outcome (Dependency/Mortality). Immediate escalation, intensive monitoring, and aggressive intervention are strongly advised.</span>
                ) : data.recovery_outcome_ml.predicted_class === 0 && data.secondary_opinion.risk_tier === 'HIGH' ? (
                  <span className="text-amber-300">⚠️ <strong>Clinical Discrepancy:</strong> The models disagree. Engine 1 predicts a good functional recovery, but Engine 2 flags a HIGH acute risk. Please manually review the patient's baseline NIHSS, imaging, and lab results before confirming the care plan.</span>
                ) : (
                  <span className="text-blue-300">ℹ️ <strong>Moderate / Mixed Outlook:</strong> The models show moderate risk or intermediate outcomes. The patient may require targeted interventions depending on specific deficits. Recommend close monitoring and customized physiotherapy.</span>
                )}
              </p>
            </div>
          )}

        </div>

        {/* ── Models used ── */}
        <div className="lg:col-span-1 bg-slate-50 border border-slate-100 rounded-3xl p-6">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <Brain size={12} /> Evidence Sources
          </h3>
          <div className="space-y-2">
            {(data?.models_used ?? []).map((m: string, i: number) => (
              <div key={i} className="text-[10px] text-slate-600 font-medium bg-white border border-slate-100 rounded-xl p-3 leading-relaxed">
                {m}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
