'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import axios from 'axios';
import { 
  ArrowLeft, User, Activity, Calendar, FileText, 
  PlusCircle, Zap, Shield, Beaker, Brain, 
  Stethoscope, LayoutTemplate, ShieldCheck,
  BrainCircuit, Droplet, Hospital
} from 'lucide-react';
import MriAnalyzerModal from '@/components/MriAnalyzerModal';
import AIChatbot from '@/components/AIChatbot';
import BrainMap from '@/components/BrainMap';

export default function PatientDashboard() {
  const params = useParams();
  const uid = params.id;
  const router = useRouter();

  const [patient, setPatient] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showMriModal, setShowMriModal] = useState(false);
  const [scanResults, setScanResults] = useState<any[]>([]);
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [pollingActive, setPollingActive] = useState(false);

  const refreshData = async () => {
    try {
      const token = localStorage.getItem('hospital_token');
      if (!token) {
        router.push('/');
        return;
      }
      const h = { headers: { Authorization: `Bearer ${token}` } };
      
      const [pRes, sRes, tRes, dRes] = await Promise.all([
        axios.get(`/api/v1/patients/${uid}`, h),
        axios.get(`/api/v1/patients/${uid}/summary`, h),
        axios.get(`/api/v1/patients/${uid}/timeline`, h),
        axios.get(`/api/v1/patients/${uid}/documents`, h)
      ]);

      setPatient(pRes.data);
      setSummary(sRes.data);
      setTimeline(tRes.data);
      setDocs(dRes.data);

      const scans = dRes.data.filter((d: any) => {
        const cat = d.category?.toLowerCase() || '';
        const type = d.file_type?.toLowerCase() || '';
        const name = d.file_name?.toLowerCase() || '';
        return cat.includes('radiology') || cat.includes('scan') || type === 'scan' || name.includes('mri') || name.includes('ct_') || name.includes('brain');
      });
      setScanResults(scans);
    } catch (err: any) {
      console.error("Dashboard error:", err);
      if (err.response?.status === 401) {
        localStorage.removeItem('hospital_token');
        router.push('/');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, [uid, router]);

  const handleOpenMriAnalysis = () => {
    setShowMriModal(true);
  };

  const calculateAge = (dob: string) => {
    if (!dob) return '??';
    const birth = new Date(dob);
    const now = new Date();
    return now.getFullYear() - birth.getFullYear();
  };

  const renderHealthScore = (label: string, score: number) => {
    const colorClass = score >= 80 ? 'bg-emerald-500' : score >= 50 ? 'bg-blue-500' : 'bg-orange-500';
    return (
      <div className="mb-4">
        <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5">
          <span>{label} Stability</span>
          <span>{score}%</span>
        </div>
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div className={`h-full ${colorClass} rounded-full transition-all duration-1000`} style={{ width: `${score}%` }} />
        </div>
      </div>
    );
  };

  // Poll for background status if polling is active
  useEffect(() => {
    if (!uid) return;
    let interval: any;
    const pollStatus = async () => {
      try {
        const token = localStorage.getItem('hospital_token');
        const h = { headers: { Authorization: `Bearer ${token}` } };
        const res = await axios.get(`/api/v1/patients/${uid}/processing-status`, h);
        setProcessingStatus(res.data);
        if (res.data.complete) {
          clearInterval(interval);
          setPollingActive(false);
          // Refresh data once complete
          if (res.data.done > 0) {
            refreshData();
          }
        }
      } catch (e) { clearInterval(interval); }
    };
    pollStatus();
    interval = setInterval(pollStatus, 4000);
    setPollingActive(true);
    return () => clearInterval(interval);
  }, [uid]);

  if (loading || !patient || !summary) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Loading Clinical Dossier...</span>
      </div>
    </div>
  );

  return (
    <div className="bg-slate-50">
      {showMriModal ? (
        <MriAnalyzerModal
          isOpen={true}
          onClose={() => setShowMriModal(false)}
          onRefresh={refreshData}
          patient={patient}
          summary={summary}
          scanData={scanResults}
        />
      ) : (
        <div className="pt-8 pb-16 px-4 md:px-8">
          <nav className="max-w-7xl mx-auto w-full mb-8 flex items-center justify-between">
            <Link href="/directory" className="flex items-center gap-2 text-slate-500 hover:text-slate-900 font-bold transition-colors">
              <ArrowLeft size={18} /> Registry
            </Link>
            <div className="flex items-center gap-4">
              <Link href={`/patient/${uid}/add-record`} className="bg-white border border-slate-200 px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-slate-50">
                <PlusCircle size={16} /> Add Clinical Event
              </Link>
              <button 
                onClick={handleOpenMriAnalysis}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-xl text-sm font-bold flex items-center gap-2 shadow-lg shadow-blue-600/20 transition-all hover:scale-105 active:scale-95"
              >
                <Zap size={16} /> AI Diagnostic Cockpit
              </button>
            </div>
          </nav>

          <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* ROW 1: Identity & Hospital Admission Overview */}
            <div className="lg:col-span-3 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm flex flex-col md:flex-row gap-8 justify-between items-start md:items-center">
              <div className="flex items-center gap-6">
                <div className="w-20 h-20 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100 shrink-0">
                  <User size={32} />
                </div>
                <div>
                  <h2 className="text-3xl font-black text-slate-900 tracking-tight leading-none mb-2">{patient.full_name}</h2>
                  <div className="flex items-center gap-3">
                    <span className="bg-slate-100 text-slate-600 text-xs font-bold px-3 py-1.5 rounded-md border border-slate-200 font-mono">{patient.patient_uid}</span>
                    <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-full ${patient.patient_category === 'geriatric' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'}`}>
                      Triage: {patient.patient_category || 'Neurological Emergency'}
                    </span>
                    <span className="text-red-500 font-black text-[10px] uppercase tracking-widest bg-red-50 px-3 py-1.5 rounded-full border border-red-100 flex items-center gap-1">
                      <Droplet size={12} /> {patient.blood_type || 'B+'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex gap-10 bg-slate-50 p-6 rounded-2xl border border-slate-100">
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-black uppercase tracking-wider mb-1">Age / DOB</span>
                  <span className="font-bold text-slate-900">{calculateAge(patient.date_of_birth)} yrs <span className="text-slate-400 font-medium ml-1">({patient.date_of_birth})</span></span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] text-blue-500 font-black uppercase tracking-wider mb-1">Admission Protocol</span>
                  <span className="font-black text-blue-700">{patient.ward_area || 'Neurology ICU'} — {patient.bed_no || 'Bed-14'}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-black uppercase tracking-wider mb-1">Diagnosis</span>
                  <span className="font-bold text-slate-900">{patient.primary_diagnosis || 'Undiagnosed / Triaging'}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-black uppercase tracking-wider mb-1">Attending Doctor</span>
                  <span className="font-bold text-slate-900 flex items-center gap-2"><Stethoscope size={14} className="text-slate-400" /> {patient.primary_doctor_id === 1 ? 'Dr. Sarah Chen' : 'Dr. Girish Motwani'}</span>
                </div>
              </div>
            </div>

            {/* ROW 1.5: Last Visited Hospital (Col 1) and Stroke AI Risk (Col 2/3) */}
            <div className="lg:col-span-1 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm flex flex-col justify-center relative overflow-hidden">
              <Hospital size={120} className="absolute -right-10 -bottom-10 text-slate-50 rotate-[-15deg] pointer-events-none" />
              <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2 relative z-10"><Calendar size={14} /> Previous Hospitalization History</h3>

              {summary?.last_hospital_visit ? (
                <div className="relative z-10">
                  <div className="text-lg font-black text-slate-900 mb-1">{summary.last_hospital_visit.hospital_name}</div>
                  <div className="text-xs font-bold text-blue-600 mb-4">{new Date(summary.last_hospital_visit.date).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}</div>
                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                    <span className="block text-[10px] text-slate-400 uppercase font-black tracking-wider mb-1">Treating Physician</span>
                    <div className="text-xs font-bold text-slate-700 mb-3">{summary.last_hospital_visit.doctor}</div>
                    <span className="block text-[10px] text-slate-400 uppercase font-black tracking-wider mb-1">Clinical Outcome</span>
                    <div className="text-xs font-medium text-slate-600 leading-snug">{summary.last_hospital_visit.outcome}</div>
                  </div>
                </div>
              ) : (
                <div className="text-slate-400 text-sm font-medium italic relative z-10">No prior hospital records detected in the clinical timeline.</div>
              )}
            </div>

            <div className="lg:col-span-2 bg-[#0a0f1d] rounded-[32px] p-10 relative overflow-hidden shadow-2xl border border-white/5 text-white flex flex-col min-h-[420px]">
              <div className="absolute -right-20 -top-20 w-80 h-80 bg-blue-600/10 blur-[100px] rounded-full"></div>
              
              <div className="flex flex-col md:flex-row gap-10 items-center flex-1">
                <div className="flex-1 w-full relative z-10">

                    {summary?.has_scan_data ? (
                      /* ── AI-CONFIRMED state ───────────────────────────────────────── */
                      (() => {
                        const rawPrediction = summary?.latest_scan?.prediction || patient?.primary_diagnosis || '';
                        const pred = rawPrediction.toLowerCase();
                        const isIschemic     = pred.includes('ischemic');
                        const isHaemorrhagic = pred.includes('haemorrhag') || pred.includes('hemorrhag');
                        const isNormalExplicit = pred.includes('no stroke') || pred.includes('normal');
                        const isGenericStroke = (pred.includes('stroke') || pred.includes('abnormal')) && !isNormalExplicit && !isIschemic && !isHaemorrhagic;

                        const confidence = Number(summary?.latest_scan?.confidence || 0);
                        const isHighConfidence = confidence > 0.8;

                        const typeLabel  = isIschemic ? (isHighConfidence ? 'ISCHEMIC STROKE DETECTED' : 'ISCHEMIC STROKE RISK')
                                        : isHaemorrhagic ? (isHighConfidence ? 'HEMORRHAGIC STROKE DETECTED' : 'HEMORRHAGIC STROKE RISK')
                                        : isGenericStroke ? 'STROKE DETECTED'
                                        : 'NO STROKE DETECTED';
                        const typeColor  = isIschemic ? 'text-blue-400'
                                        : isHaemorrhagic ? 'text-orange-400'
                                        : isGenericStroke ? 'text-red-400'
                                        : 'text-emerald-400';
                        const badgeColor = isIschemic ? 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                                        : isHaemorrhagic ? 'bg-orange-500/10 border-orange-500/20 text-orange-400'
                                        : isGenericStroke ? 'bg-red-500/10 border-red-500/20 text-red-400'
                                        : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
                        const actColor   = isIschemic ? 'text-blue-400'
                                        : isHaemorrhagic ? 'text-orange-400'
                                        : isGenericStroke ? 'text-red-400'
                                        : 'text-emerald-400';

                        return (
                          <div className="flex items-start gap-3 mb-8">
                            <Activity size={20} className={`${actColor} mt-2 shrink-0`} />
                            <div className="flex flex-col">
                              <span className={`text-[9px] font-black uppercase tracking-[0.25em] ${typeColor} opacity-70 mb-2`}>
                                AI Confirmed · VGG19 Ensemble
                              </span>
                              <h2 className={`text-5xl font-black leading-[0.9] tracking-tighter uppercase max-w-[300px] mb-3 ${typeColor}`}>
                                {typeLabel.split(' ').map((word: string, i: number) => (
                                  <span key={i} className="block">{word}</span>
                                ))}
                              </h2>
                              <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[8px] font-black uppercase tracking-widest ${badgeColor}`}>
                                <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                                {summary?.latest_scan?.confidence
                                  ? `${(Number(summary.latest_scan.confidence) * 100).toFixed(1)}% AI Confidence`
                                  : 'Confidence Pending'}
                              </div>
                            </div>
                          </div>
                        );
                      })()
                    ) : (
                      /* ── NO-SCAN state (matches registry card exactly) ────────────────── */
                      <div className="mb-8">
                        <div className="flex items-center gap-2 mb-3">
                          <Activity size={14} className="text-slate-500" />
                          <span className="text-[9px] font-black uppercase tracking-[0.25em] text-slate-500">Preliminary Admission Diagnosis</span>
                        </div>
                        <h2 className="text-5xl font-black text-slate-400 leading-[0.9] tracking-tighter uppercase max-w-[300px] mb-4">
                          {(patient?.primary_diagnosis || 'Undiagnosed')
                            .split(' ').map((word: string, i: number) => (
                              <span key={i} className="block">{word}</span>
                            ))}
                        </h2>
                        <div className="inline-flex items-center gap-2 bg-slate-800/60 border border-white/5 px-3 py-1.5 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse" />
                          <span className="text-[8px] font-black uppercase tracking-widest text-slate-500">Not AI-Verified · Upload scan for analysis</span>
                        </div>
                      </div>
                    )}


                    <div className="bg-slate-800/40 border border-white/5 p-4 rounded-2xl inline-flex flex-col gap-1 mb-8 min-w-[120px]">
                        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Prior Strokes:</span>
                        <span className="text-2xl font-black text-white leading-none">{summary?.prior_strokes ?? 0}</span>
                    </div>

                    <div className="space-y-4">
                        <p className="text-slate-400 text-sm font-medium italic">
                            {(!summary?.alerts || summary?.alerts?.length === 0) && !summary?.adherence_flag 
                                ? "No active severe physiological alerts detected."
                                : summary?.alerts?.[0]?.message || "Clinical vigilance advised."}
                        </p>
                        
                        <div className="flex flex-wrap gap-3">
                            {Array.from(new Set(summary?.preventive_health_report?.ischemic_factors?.map((f: any) => f.message)))
                                .slice(0, 3)
                                .map((message: any, i: number) => (
                                <div key={i} className="bg-red-500/5 border border-red-500/20 px-4 py-2 rounded-full text-[10px] font-black text-red-400 uppercase tracking-widest flex items-center gap-2">
                                    <Activity size={12}/> {message}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>


                <div className="w-full md:w-[320px] shrink-0 relative z-10">
                    <BrainMap 
                        diagnosis={patient?.primary_diagnosis} 
                        patientUid={patient?.patient_uid} 
                        volume={summary?.latest_scan?.volume_percentage ?? null}
                        confidence={summary?.latest_scan?.confidence ?? null}
                        side={summary?.latest_scan?.side ?? null}
                        x={summary?.latest_scan?.lesion_center_x ?? null}
                        y={summary?.latest_scan?.lesion_center_y ?? null}
                    />
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-white/5 flex justify-center opacity-40">
                 <span className="text-[9px] font-black uppercase text-slate-400 tracking-[0.3em]">Powered by Gemini-2.0-Flash Multi-Modal Intelligence</span>
              </div>
            </div>

            {/* ROW 2: Labs & Timeline */}
            <div className="lg:col-span-3 grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Labs Column */}
              <div className="lg:col-span-1 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm flex flex-col h-[850px] overflow-hidden">
                <h3 className="text-slate-900 font-bold text-lg mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-2"><Beaker size={18} className="text-purple-600" /> Recent Lab Investigations</div>
                </h3>

                <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-2">
                  {!summary?.recent_lab_details || summary?.recent_lab_details.length === 0 ? (
                    <div className="text-center py-10 text-slate-400 text-sm italic border-2 border-dashed border-slate-100 rounded-xl">No Recent Diagnostics Found.</div>
                  ) : (
                    summary.recent_lab_details.map((lab: any, i: number) => (
                      <div key={i} className={`p-4 rounded-xl border ${lab.status?.toLowerCase() === 'abnormal' ? 'bg-orange-50/50 border-orange-200' : 'bg-slate-50 border-slate-100'}`}>
                        <div className="flex justify-between items-start mb-2">
                          <div className="font-bold text-sm text-slate-800">{lab.test_name}</div>
                          <div className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${lab.status?.toLowerCase() === 'abnormal' ? 'bg-orange-200 text-orange-800' : 'bg-green-100 text-green-700'}`}>
                            {lab.status || 'Normal'}
                          </div>
                        </div>
                        <div className="flex items-end gap-2 mb-3">
                          <span className={`text-xl font-black ${lab.status?.toLowerCase() === 'abnormal' ? 'text-orange-600' : 'text-slate-900'}`}>{lab.value}</span>
                          <span className="text-xs font-bold text-slate-400 mb-1">{lab.unit}</span>
                          {lab.trend && lab.trend !== 'stable' && (
                            <div className={`ml-auto flex items-center gap-1 text-[10px] font-black uppercase px-2 py-1 rounded-lg ${lab.trend === 'up' ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
                              {lab.trend === 'up' ? '↑ Rising' : '↓ Falling'}
                            </div>
                          )}
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-slate-200/60 mt-2">
                          <span className="text-[9px] text-slate-400 uppercase tracking-widest font-black">Ordered by {lab.ordered_by}</span>
                          <span className="text-[9px] text-slate-400 font-bold">{lab.date ? new Date(lab.date).toLocaleDateString() : ''}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Timeline Column */}
              <div className="lg:col-span-2 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm flex flex-col h-[850px] overflow-hidden">
                <h3 className="text-slate-900 font-bold text-lg mb-6 flex items-center gap-2"><Calendar size={18} className="text-blue-600" /> Clinical Timeline (Longitudinal)</h3>

                <div className="flex gap-4 overflow-x-auto pb-6 custom-scrollbar flex-1">
                  {timeline.length === 0 ? (
                    <div className="text-slate-400 text-sm italic py-4">No events found.</div>
                  ) : (
                    timeline.map((group, i) => (
                      <div key={i} className="min-w-[280px] border-l-2 border-slate-200 pl-4 relative pt-2 flex flex-col h-full">
                        <div className="absolute w-3 h-3 bg-blue-600 rounded-full -left-[7px] top-3 ring-4 ring-white"></div>
                        <div className="text-[10px] font-black uppercase tracking-widest text-blue-600 mb-3">{group.label}</div>
                        <div className="space-y-3 overflow-y-auto pr-2 custom-scrollbar flex-1">
                          {group.events.map((ev: any) => {
                            const isAi = ev.title.includes('AI:');
                            const isLab = ev.type === 'document_analysis' && ev.title.includes('Lab');
                            const isSurgery = ev.type === 'surgery';

                            return (
                              <div key={ev.id} className="bg-slate-50 border border-slate-100 p-4 rounded-xl text-sm font-medium text-slate-700 hover:border-blue-200 transition-colors flex gap-4">
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isAi ? 'bg-purple-100 text-purple-600' : isLab ? 'bg-blue-100 text-blue-600' : isSurgery ? 'bg-orange-100 text-orange-600' : 'bg-slate-200 text-slate-500'}`}>
                                  {isAi ? <BrainCircuit size={18} /> : isLab ? <Beaker size={18} /> : isSurgery ? <Activity size={18} /> : <FileText size={18} />}
                                </div>
                                <div>
                                  <div className="text-[10px] text-slate-400 uppercase font-black tracking-tight mb-1">{ev.type.replace('_', ' ')}</div>
                                  <div className="text-slate-900 font-bold">{ev.title}</div>
                                  <div className="text-[10px] text-slate-400 mt-1">{new Date(ev.date).toLocaleDateString()}</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* ROW 3: Medical Summary & Documents */}
            <div className="lg:col-span-2 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
              <h3 className="text-slate-900 font-bold text-lg mb-6 flex items-center gap-2"><Shield size={18} className="text-purple-600" /> Preventive Health & Vulnerability Report</h3>


              {summary?.has_real_data ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                  <div className="flex flex-col gap-8">
                    <div>
                      <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-6">Healthiness Metrics</h4>
                      {renderHealthScore('Cardiovascular', summary?.preventive_health_report?.healthiness_scores?.cardiovascular ?? 100)}
                      {renderHealthScore('Metabolic', summary?.preventive_health_report?.healthiness_scores?.metabolic ?? 100)}
                      {renderHealthScore('Vascular', summary?.preventive_health_report?.healthiness_scores?.vascular ?? 100)}
                      {renderHealthScore('Neurological', summary?.preventive_health_report?.healthiness_scores?.neurological ?? 100)}
                    </div>

                    <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
                      <div className="flex items-center gap-2 text-indigo-700 font-bold text-sm mb-3"><BrainCircuit size={16} /> Radiological Intelligence Insight</div>
                      <div className="text-xs text-indigo-900 leading-relaxed font-medium">
                          {summary?.has_scan_data
                            ? (summary?.latest_scan?.xai_analysis || 'AI analysis complete. See scan details in the Document Vault.')
                            : 'No radiology scan has been processed yet. Upload an MRI or CT scan and run AI analysis in the Document Vault to generate insights.'}
                      </div>
                      <div className="mt-3 flex items-center gap-2 text-[8px] font-black uppercase text-indigo-400 tracking-widest">
                          <ShieldCheck size={10} /> {summary?.has_scan_data ? 'Verified via VGG19 Ensemble' : 'Awaiting Scan Input'}
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-6">Cleveland Clinic Vectors</h4>

                    <div className={`${summary?.latest_scan?.prediction?.toLowerCase().includes('ischemic') ? 'bg-red-50 border border-red-200 shadow-sm' : 'bg-slate-50 border border-slate-100 opacity-60'} rounded-xl p-5 mb-4 transition-all duration-500`}>
                      <div className={`flex items-center gap-2 ${summary?.latest_scan?.prediction?.toLowerCase().includes('ischemic') ? 'text-red-600' : 'text-slate-500'} font-bold text-sm mb-2`}>
                          {summary?.latest_scan?.prediction?.toLowerCase().includes('ischemic') ? '🔴' : '🟢'} {summary?.has_scan_data && summary?.latest_scan?.prediction && summary.latest_scan.prediction.toLowerCase().includes('ischemic')
                              ? summary.latest_scan.prediction.replace(/\(.*\)/g, '').replace('Detected', '').trim() + ' Confirmed'
                              : 'Ischemic Stroke Risk'}
                      </div>
                      {summary?.preventive_health_report?.ischemic_vulnerability ? (
                        <ul className={`text-xs font-medium ${summary?.latest_scan?.prediction?.toLowerCase().includes('ischemic') ? 'text-red-800' : 'text-slate-600'} list-disc ml-4 space-y-2`}>
                          {Array.from(new Set(summary.preventive_health_report.ischemic_factors.map((f: any) => JSON.stringify(f))))
                            .map((s: any) => JSON.parse(s))
                            .map((f: any, i: number) => (
                            <li key={i}>
                              <div className="font-bold">{f.message}</div>
                              <div className={`text-[9px] ${summary?.latest_scan?.prediction?.toLowerCase().includes('ischemic') ? 'text-red-500' : 'text-slate-400'} uppercase font-black tracking-widest mt-0.5 flex items-center gap-1`}>
                                <FileText size={10} /> Source: {f.evidence}
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : <div className="text-xs text-slate-400 italic">No historical triggers detected.</div>}
                    </div>

                    <div className={`${summary?.latest_scan?.prediction?.toLowerCase().includes('haemorrhagic') ? 'bg-orange-50 border border-orange-200 shadow-sm' : 'bg-slate-50 border border-slate-100 opacity-60'} rounded-xl p-5 mb-4 transition-all duration-500`}>
                      <div className={`flex items-center gap-2 ${summary?.latest_scan?.prediction?.toLowerCase().includes('haemorrhagic') ? 'text-orange-600' : 'text-slate-500'} font-bold text-sm mb-2`}>
                          {summary?.latest_scan?.prediction?.toLowerCase().includes('haemorrhagic') ? '🔴' : '🟢'} {summary?.has_scan_data && summary?.latest_scan?.prediction && summary.latest_scan.prediction.toLowerCase().includes('haemorrhagic')
                              ? summary.latest_scan.prediction.replace(/\(.*\)/g, '').replace('Detected', '').trim() + ' Confirmed'
                              : 'Hemorrhagic Stroke Risk'}
                      </div>
                      {summary?.preventive_health_report?.hemorrhagic_vulnerability ? (
                        <ul className="text-xs font-medium text-orange-800 list-disc ml-4 space-y-2">
                          {summary.preventive_health_report.hemorrhagic_factors.map((f: any, i: number) => (
                            <li key={i}>
                              <div className="font-bold">{f.message}</div>
                              <div className="text-[9px] text-orange-500 uppercase font-black tracking-widest mt-0.5 flex items-center gap-1">
                                <FileText size={10} /> Source: {f.evidence}
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : <div className="text-xs text-slate-500 italic">No historical triggers detected.</div>}
                    </div>

                    <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
                      <div className="flex items-center gap-2 text-blue-700 font-bold text-sm mb-4"><Stethoscope size={16} /> Precision Clinical Next-Steps</div>
                      <div className="space-y-4">
                        {summary?.preventive_health_report?.recommendations?.map((rec: any, i: number) => (
                          <div key={i} className="flex gap-3">
                            <div className={`w-6 h-6 rounded-lg text-white flex items-center justify-center shrink-0 text-[10px] font-black shadow-md ${rec?.priority?.includes('Critical') ? 'bg-red-500 shadow-red-200' : 'bg-blue-600 shadow-blue-200'}`}>{i + 1}</div>
                            <div className="flex flex-col gap-1">
                                <div className="text-xs font-bold text-blue-950 leading-tight">{typeof rec === 'string' ? rec : rec?.title}</div>
                                {typeof rec !== 'string' && rec?.content && (
                                  <div className="text-[9px] text-slate-500 leading-relaxed">{rec.content}</div>
                                )}
                                <div className={`text-[9px] font-black uppercase tracking-tighter ${rec?.priority?.includes('Critical') ? 'text-red-500' : 'text-blue-500'}`}>
                                  Priority: {typeof rec === 'string' ? (i === 0 ? 'Critical / STAT' : 'Routine Clinical') : (rec?.priority || 'Routine Clinical')}
                                </div>
                            </div>
                          </div>
                        )) || (
                          <div className="text-xs text-slate-400 italic">Formulating clinical protocol based on current vectors...</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 gap-4 border-2 border-dashed border-slate-100 rounded-2xl">
                  <div className="w-14 h-14 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center">
                    <Shield size={24} className="text-slate-300" />
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-slate-500 text-sm mb-1">No Clinical Data Available</p>
                    <p className="text-[11px] text-slate-400 max-w-[300px] leading-relaxed">
                      Upload lab reports, radiology scans, ECG signals, or clinical records in the
                      {' '}<button onClick={() => router.push(`/patient/${uid}/documents`)} className="text-blue-500 font-bold hover:underline">Document Vault</button>{' '}
                      to enable AI-powered risk analysis.
                    </p>
                  </div>
                </div>
              )}
            </div>


            <div className="lg:col-span-1 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm flex flex-col h-[550px]">
              <h3 className="text-slate-900 font-bold text-lg mb-6 flex items-center justify-between">
                <div className="flex items-center gap-2"><FileText size={18} className="text-blue-600" /> Documents Collection</div>
                <button onClick={() => router.push(`/patient/${uid}/documents`)} title="Open Full Vault Viewer" className="px-4 py-2 bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white rounded-xl font-bold text-[10px] uppercase tracking-widest transition-colors flex items-center gap-2">
                  <LayoutTemplate size={14} /> Side-By-Side Vault
                </button>
              </h3>

              {/* Processing Progress Bar */}
              {processingStatus && processingStatus.total > 0 && (
                <div className={`mb-4 p-4 rounded-2xl border ${processingStatus.complete ? 'bg-green-50 border-green-100' : 'bg-blue-50 border-blue-100'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Background Analysis</span>
                    <span className={`text-[10px] font-black ${processingStatus.complete ? 'text-green-600' : 'text-blue-600'}`}>
                      {processingStatus.done}/{processingStatus.total} Documents
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${processingStatus.complete ? 'bg-green-500' : 'bg-blue-500 animate-pulse'}`}
                      style={{ width: `${processingStatus.percent}%` }}
                    />
                  </div>
                  {!processingStatus.complete && (
                    <div className="text-[10px] text-blue-500 font-medium mt-1 flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                      Processing — OCR & AI models running in background...
                    </div>
                  )}
                </div>
              )}

              <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-2">
                {docs.length === 0 ? (
                  <div className="text-center py-10 text-slate-400 text-sm italic border-2 border-dashed border-slate-100 rounded-xl">No documents extracted.</div>
                ) : (
                  docs.map((d, index) => (
                    <div key={d.id} className="flex items-center justify-between p-3 border border-slate-100 bg-slate-50 rounded-xl hover:border-blue-300 transition-colors cursor-pointer group" onClick={() => router.push(`/patient/${uid}/documents?index=${index}`)}>
                      <div className="flex items-center gap-3">
                        <FileText size={16} className="text-blue-500 group-hover:scale-110 transition-transform" />
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate-700 truncate max-w-[150px]">{d.file_name}</span>
                          <span className="text-[9px] text-slate-400 font-black tracking-widest mt-0.5">{new Date(d.upload_date).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Scan</span>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
          <AIChatbot patientUid={uid as string} />
        </div>
      )}
    </div>
  );
}
