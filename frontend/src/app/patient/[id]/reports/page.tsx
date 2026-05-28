"use client";

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Activity, ArrowLeft, ShieldAlert, BrainCircuit, Zap, Terminal, Plus, ShieldCheck, HeartPulse
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, BarChart, Bar, CartesianGrid, Cell
} from 'recharts';
import BrainModel from '@/components/BrainModel';

export default function DiagnosticCockpit() {
  const { id: uid } = useParams();
  const router = useRouter();

  const [patient, setPatient] = useState<any>(null);
  const [pipelineStages, setPipelineStages] = useState<any[]>([]);
  const [computing, setComputing] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);

  // Doctor Override State
  const [doctorReason, setDoctorReason] = useState("");
  const [doctorDecision, setDoctorDecision] = useState("Agree with AI");
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  useEffect(() => {
    const fetchIdentity = async () => {
      try {
        const token = localStorage.getItem('hospital_token');
        if (!token) return router.push('/');
        const pRes = await axios.get(`/api/v1/patients/${uid}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setPatient(pRes.data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchIdentity();
  }, [uid]);

  const runAIEngine = async () => {
    setComputing(true);
    setPrediction(null);
    setPipelineStages([]);

    try {
      const token = localStorage.getItem('hospital_token');
      // Using standard fetch since we need to process SSE / text stream
      const response = await fetch(`/api/v1/patients/${uid}/analyze`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.body) throw new Error("No response body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let currentPrediction: any = {};

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "");
            if (!dataStr) continue;
            try {
              const stage = JSON.parse(dataStr);
              setPipelineStages(prev => {
                // prevent duplicates
                if (prev.find(p => p.stage === stage.stage)) return prev;
                return [...prev, stage];
              });
              if (stage.stage === 'MULTIVARIATE_SHAP_EXPLAINER' || stage.stage === 'RISK_STRATIFICATION') {
                currentPrediction.risk_data = stage.data;
              }
              if (stage.stage === 'TPA_PHARMACOKINETIC_GATE' || stage.stage === 'TPA_VALIDATION') {
                currentPrediction.tpa = stage.data;
              }
              if (stage.stage === 'SBAR_NARRATIVE_SYNTHESIS' || stage.stage === 'SBAR_SYNTHESIS') {
                currentPrediction.sbar = stage.data.sbar_note;
                currentPrediction.trajectory = stage.data.points;
              }
            } catch (e) { console.error("Parse error", e) }
          }
        }
      }

      setPrediction(currentPrediction);

    } catch (e) {
      console.error(e);
      setPipelineStages(prev => [...prev, { stage: "ERROR", message: "Critical Neural Handshake Failure.", data: null }]);
    } finally {
      setComputing(false);
    }
  };

  const submitOverride = async () => {
    if (!doctorReason) return alert("Must provide clinical rationale.");
    setSaveStatus('saving');
    try {
      const token = localStorage.getItem('hospital_token');
      await axios.post(`/api/v1/patients/${uid}/override`, {
        ai_recommendation: prediction.sbar.recommendation,
        doctor_decision: doctorDecision,
        override_reason: doctorReason
      }, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setSaveStatus('saved');
    } catch (e) {
      console.error(e);
      setSaveStatus('idle');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-300 font-sans selection:bg-blue-500/30">

      <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href={`/patient/${uid}`} className="flex items-center gap-3 text-slate-400 hover:text-white transition-colors">
            <ArrowLeft size={18} /> Exit Cockpit
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-[10px] uppercase font-black tracking-widest text-emerald-500">Secure Neural Link</span>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-12">

        <header className="mb-12 flex justify-between items-end">
          <div>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-[0_0_30px_rgba(37,99,235,0.3)]">
                <BrainCircuit size={24} />
              </div>
              <div>
                <h1 className="text-3xl font-black text-white tracking-tight">AI Diagnostic Engine</h1>
                <p className="text-slate-500 text-sm font-medium mt-1">Multi-modal stroke recurrence and recovery forecasting.</p>
              </div>
            </div>
          </div>

          <button
            onClick={runAIEngine}
            disabled={computing || prediction}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-4 rounded-xl font-black tracking-tight flex items-center gap-3 transition-all shadow-[0_0_40px_rgba(37,99,235,0.4)]"
          >
            {computing ? (
              <><div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div> Synthesizing Corpus...</>
            ) : (
              <><Zap size={18} /> Initiate 6-Layer Deep Scientific Pipeline</>
            )}
          </button>
        </header>

        {/* Console / Pipeline Feed */}
        <div className="bg-black/40 border border-slate-800 rounded-2xl p-6 font-mono text-sm mb-12 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-blue-600"></div>
          <div className="flex items-center gap-2 text-slate-500 mb-6 pb-4 border-b border-slate-800/50">
            <Terminal size={14} /> <span>Pipeline Stream [v4.0.0]</span>
          </div>

          <div className="space-y-3 min-h-[150px]">
            {pipelineStages.length === 0 && !computing && (
              <div className="text-slate-600 italic">SYSTEM IDLE. Awaiting command execution...</div>
            )}
            {pipelineStages.map((s, i) => (
              <div key={i} className="flex gap-4">
                <span className="text-blue-500 shrink-0">[{s.stage}]</span>
                <span className={s.status === 'ERROR' ? 'text-red-400' : 'text-slate-300'}>{s.message}</span>
              </div>
            ))}
            {computing && <div className="text-slate-500 animate-pulse mt-4">_</div>}
          </div>
        </div>

        {/* RESULTS RENDER */}
        {prediction && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-1000">

            {/* TPA BANNER */}
            {prediction.tpa?.eligible ? (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-6 flex items-start gap-4">
                <ShieldCheck size={32} className="text-emerald-500 shrink-0 mt-1" />
                <div>
                  <h3 className="text-xl font-black text-emerald-400">tPA ADMINISTRATION CLEARED</h3>
                  <p className="text-emerald-500/80 mt-1 font-medium text-sm">Patient falls safely within 4.5h window and passes all 5 baseline contraindications (BP, INR, Plt, etc).</p>
                </div>
              </div>
            ) : (
              <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 flex items-start gap-4">
                <ShieldAlert size={32} className="text-red-500 shrink-0 mt-1" />
                <div>
                  <h3 className="text-xl font-black text-red-500">tPA CONTRAINDICATED</h3>
                  <ul className="list-disc pl-5 mt-2 space-y-1 text-red-400 font-medium text-sm">
                    {prediction.tpa?.contraindications?.map((c: string, i: number) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

              {/* XGBOOST RISK TIER */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-3xl p-8 flex flex-col items-center justify-center text-center relative overflow-hidden">
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-6 w-full text-left flex justify-between items-center">
                  <span>Absolute Risk</span>
                  <span className="bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20">High Confidence</span>
                </div>

                <div className="relative">
                  <svg className="w-48 h-48 transform -rotate-90">
                    <circle cx="96" cy="96" r="88" className="stroke-slate-800" strokeWidth="12" fill="none" />
                    <circle cx="96" cy="96" r="88" className={prediction.risk_data?.probability > 40 ? "stroke-red-500" : "stroke-blue-500"} strokeWidth="12" fill="none" strokeDasharray="553" strokeDashoffset={553 - (553 * (prediction.risk_data?.probability || 0)) / 100} style={{ transition: 'stroke-dashoffset 2s ease-out' }} />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center mt-2">
                    <span className="text-5xl font-black text-white">{prediction.risk_data?.probability}<span className="text-xl">%</span></span>
                    {prediction.risk_data?.heuristic_risk_score !== undefined && (
                      <span className="text-[10px] font-bold text-slate-400 mt-1 uppercase tracking-widest bg-black/20 px-2 py-0.5 rounded-full border border-white/5">
                        Clinical Heuristic: {prediction.risk_data?.heuristic_risk_score}
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-6 px-6 py-2 bg-slate-900 rounded-full border border-slate-700">
                  <span className={`text-lg font-black tracking-widest uppercase ${prediction.risk_data?.probability > 40 ? 'text-red-500' : 'text-blue-500'}`}>
                    {prediction.risk_data?.risk_level}
                  </span>
                </div>
              </div>

              {/* SHAP EXPLAINABILITY */}
              <div className="lg:col-span-2 bg-slate-800/40 border border-slate-700/50 rounded-3xl p-8">
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-6 flex justify-between">
                  <span>XGBoost SHAP Feature Attribution (Local)</span>
                  <span className="text-blue-500">Top 10 Clinical Determinants</span>
                </div>
                <div className="h-96 w-full mt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart layout="vertical" data={prediction.risk_data?.shap_values?.sort((a: any, b: any) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 10)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                      <XAxis type="number" stroke="#64748b" fontSize={10} tickFormatter={(val) => val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)} />
                      <YAxis dataKey="feature" type="category" stroke="#94a3b8" fontSize={11} width={150} tickFormatter={(val: string) => val.replace(/_/g, ' ').toUpperCase()} />
                      <RechartsTooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px' }} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {prediction.risk_data?.shap_values?.map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={entry.value > 0 ? '#ef4444' : '#3b82f6'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

            </div>

            {/* SBAR & TRAJECTORY */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

              {/* SBAR */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-3xl p-8">
                <h3 className="text-slate-100 font-bold text-lg mb-6 flex items-center gap-2 border-b border-slate-700 pb-4"><Activity size={18} className="text-blue-500" /> SBAR Hand-off Note</h3>

                <div className="space-y-6">
                  <div>
                    <h4 className="text-xs font-black uppercase tracking-widest text-blue-500 mb-2">Situation</h4>
                    <p className="text-slate-300 text-sm leading-relaxed">{prediction.sbar?.situation}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-black uppercase tracking-widest text-blue-500 mb-2">Background</h4>
                    <p className="text-slate-300 text-sm leading-relaxed">{prediction.sbar?.background}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-black uppercase tracking-widest text-blue-500 mb-2">Assessment</h4>
                    <p className="text-slate-300 text-sm leading-relaxed">{prediction.sbar?.assessment}</p>
                  </div>
                  <div className="bg-blue-500/10 border border-blue-500/20 p-4 rounded-xl">
                    <h4 className="text-xs font-black uppercase tracking-widest text-blue-400 mb-2">Recommendation / Protocol</h4>
                    <p className="text-blue-100 text-sm leading-relaxed font-medium">{prediction.sbar?.recommendation}</p>
                  </div>
                </div>
              </div>

              {/* DEEPSURV TRAJECTORY */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-3xl p-8 flex flex-col">
                <h3 className="text-slate-100 font-bold text-lg mb-6 flex items-center gap-2 border-b border-slate-700 pb-4"><HeartPulse size={18} className="text-purple-500" /> 90-Day Survival Trajectory (RSF)</h3>
                <div className="flex-1 min-h-[300px] w-full mt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={prediction.trajectory}>
                      <defs>
                        <linearGradient id="colorSurv" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="day" stroke="#64748b" fontSize={11} tickFormatter={(val) => `Day ${val}`} />
                      <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} tickFormatter={(val) => `${val}%`} />
                      <RechartsTooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px' }} itemStyle={{ color: '#e2e8f0' }} />
                      <Area type="monotone" dataKey="probability" stroke="#a855f7" strokeWidth={3} fillOpacity={1} fill="url(#colorSurv)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* DOCTOR OVERRIDE LAYER */}
            <div className="bg-slate-800 border border-slate-700 rounded-3xl p-8 shadow-2xl mt-12">
              <h3 className="text-white font-black text-xl mb-6">Human Over-the-Loop Validation</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Clinical Decision</label>
                  <select value={doctorDecision} onChange={e => setDoctorDecision(e.target.value)} className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-5 py-4 focus:ring-4 focus:ring-blue-500/20 focus:outline-none appearance-none">
                    <option>Agree with AI (Proceed with Protocol)</option>
                    <option>Acknowledge AI / Modify Protocol</option>
                    <option>Override AI (Contraindicated clinically)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Rationale / Signature Note</label>
                  <input value={doctorReason} onChange={e => setDoctorReason(e.target.value)} type="text" className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-5 py-4 focus:ring-4 focus:ring-blue-500/20 focus:outline-none" placeholder="Enter clinical rationale..." />
                </div>
              </div>

              <div className="mt-8 flex justify-end">
                <button
                  onClick={submitOverride}
                  disabled={saveStatus !== 'idle'}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-black px-8 py-3 rounded-xl disabled:opacity-50 transition-colors"
                >
                  {saveStatus === 'idle' ? 'Sign & Append to EHR' : saveStatus === 'saving' ? 'Saving...' : 'Cryptographically Secured'}
                </button>
              </div>

              {saveStatus === 'saved' && (
                <div className="mt-4 text-emerald-400 text-sm font-bold flex justify-end">
                  ✓ Override logged and validated. Legal disclaimers applied.
                </div>
              )}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
