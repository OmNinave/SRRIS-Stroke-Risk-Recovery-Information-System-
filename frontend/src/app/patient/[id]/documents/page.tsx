"use client";

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ChevronLeft, ChevronRight, FileText, Download, LayoutTemplate, FolderOpen, Folder, ScanEye, ShieldAlert, Activity, BrainCircuit, Beaker, Zap, Microscope, Camera, PenLine } from 'lucide-react';
import gsap from 'gsap';

export default function DocumentVaultPage() {
  const { id: uid } = useParams();
  const router = useRouter();

  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [activeCategory, setActiveCategory] = useState<string>('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [enableAi, setEnableAi] = useState(false);
  const [scanningDocId, setScanningDocId] = useState<number | null>(null);
  const [scanPhase, setScanPhase] = useState<number>(0);
  const [scanResult, setScanResult] = useState<any>(null);
  const [vizMode, setVizMode] = useState<'heatmap' | 'detection'>('heatmap');

  const scanCacheKey = (docId: number) => `srris_scan_cache:${uid}:${docId}`;

  const scanTimersRef = useRef<{
    phaseInterval: NodeJS.Timeout | null;
    pollInterval: NodeJS.Timeout | null;
    hardTimeout: NodeJS.Timeout | null;
  }>({ phaseInterval: null, pollInterval: null, hardTimeout: null });

  const clearScanTimers = () => {
    if (scanTimersRef.current.phaseInterval) clearInterval(scanTimersRef.current.phaseInterval);
    if (scanTimersRef.current.pollInterval) clearInterval(scanTimersRef.current.pollInterval);
    if (scanTimersRef.current.hardTimeout) clearTimeout(scanTimersRef.current.hardTimeout);
    scanTimersRef.current.phaseInterval = null;
    scanTimersRef.current.pollInterval = null;
    scanTimersRef.current.hardTimeout = null;
  };

  // Grouping documents by category (Folders)
  const groupedDocs = docs.reduce((acc: any, doc: any) => {
    const cat = doc.category || "General Records";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(doc);
    return acc;
  }, {});

  const categories = Object.keys(groupedDocs);
  const currentCategoryDocs = groupedDocs[activeCategory] || [];
  const activeDoc = currentCategoryDocs.length > 0 ? currentCategoryDocs[activeIndex] : null;

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const token = localStorage.getItem('hospital_token');
        if (!token) return router.push('/');
        const headers = { Authorization: `Bearer ${token}` };

        const res = await axios.get(`/api/v1/patients/${uid}/documents`, { headers });
        setDocs(res.data);

        // Derive first category to auto-select
        if (res.data.length > 0) {
           const firstCat = res.data[0].category || "General Records";
           setActiveCategory(firstCat);
        }

        setTimeout(() => {
          gsap.fromTo('.vault-anim', { opacity: 0, y: 15 }, { opacity: 1, y: 0, stagger: 0.1, duration: 0.6, ease: "power2.out" });
        }, 50);

      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [uid, router]);

  useEffect(() => {
    return () => {
      clearScanTimers();
    };
  }, []);

  // Reload last scan result for currently selected document (survives refresh)
  useEffect(() => {
    if (!uid) return;
    if (!activeDoc?.id) return;
    try {
      const raw = localStorage.getItem(scanCacheKey(activeDoc.id));
      if (!raw) {
        setScanResult(null);
        setEnableAi(false);
        return;
      }
      const parsed = JSON.parse(raw);
      setScanResult(parsed);
      setEnableAi(true);
    } catch {
      setScanResult(null);
      setEnableAi(false);
    }
  }, [uid, activeDoc?.id]);

  const handleStartScan = async () => {
    if (!activeDoc) return;
    clearScanTimers();
    setScanningDocId(activeDoc.id);
    setScanResult(null);
    setEnableAi(false);
    setScanPhase(1);
    try { localStorage.removeItem(scanCacheKey(activeDoc.id)); } catch {}
    
    const phaseInterval = setInterval(() => {
      setScanPhase(prev => (prev < 4 ? prev + 1 : prev));
    }, 1200);
    scanTimersRef.current.phaseInterval = phaseInterval;
    
    try {
      const token = localStorage.getItem('hospital_token');
      const headers = { Authorization: `Bearer ${token}` };
      
      await axios.post(`/api/v1/patients/${uid}/scan/${activeDoc.id}`, {}, { headers });
      
      const pollInterval = setInterval(async () => {
        try {
          const poll = await axios.get(`/api/v1/patients/${uid}/scan-status/${activeDoc.id}`, { headers });
          if (poll.data.status === 'done' || poll.data.status === 'error' || poll.data.status === 'not_started' || poll.data.status === 'success') {
            clearScanTimers();
            setScanPhase(4);
            setTimeout(() => {
              setScanResult(poll.data);
              setScanningDocId(null);
              setEnableAi(true);
              try { localStorage.setItem(scanCacheKey(activeDoc.id), JSON.stringify(poll.data)); } catch {}
            }, 500);
          }
        } catch (pollErr) {
          clearScanTimers();
          setScanningDocId(null);
          console.error('Scan poll error:', pollErr);
        }
      }, 3000);
      scanTimersRef.current.pollInterval = pollInterval;
      
      const hardTimeout = setTimeout(() => {
        clearScanTimers();
        setScanningDocId(null);
        const timeoutResult = {
          status: 'timeout',
          doc_id: activeDoc.id,
          prediction: 'Timed out',
          confidence: 0,
          ocr_text: 'Scan timed out after 3 minutes. Try again, or check backend logs for the job.',
          xai_analysis: 'Radiology scan job did not return results within the UI timeout window.',
          markers: {}
        };
        setScanResult(timeoutResult);
        setEnableAi(true);
        try { localStorage.setItem(scanCacheKey(activeDoc.id), JSON.stringify(timeoutResult)); } catch {}
      }, 180000);
      scanTimersRef.current.hardTimeout = hardTimeout;

    } catch (err) {
      console.error('Scan start error:', err);
      clearScanTimers();
      setScanningDocId(null);
      setScanPhase(0);
    }
  };

  const handleEcgScan = async () => {
    if (!activeDoc) return;
    clearScanTimers();
    setScanningDocId(activeDoc.id);
    setScanResult(null);
    setEnableAi(false);
    setScanPhase(1);
    try { localStorage.removeItem(scanCacheKey(activeDoc.id)); } catch {}
    
    try {
      const token = localStorage.getItem('hospital_token');
      const headers = { Authorization: `Bearer ${token}` };
      
      await axios.post(`/api/v1/patients/${uid}/scan-ecg/${activeDoc.id}`, {}, { headers });
      
      const pollInterval = setInterval(async () => {
        try {
          const poll = await axios.get(`/api/v1/patients/${uid}/ecg-status/${activeDoc.id}`, { headers });
          if (poll.data.status === 'done' || poll.data.status === 'error' || poll.data.status === 'not_started') {
            clearScanTimers();
            setScanResult(poll.data);
            setScanningDocId(null);
            setEnableAi(true);
            try { localStorage.setItem(scanCacheKey(activeDoc.id), JSON.stringify(poll.data)); } catch {}
          }
        } catch (pollErr) {
          clearScanTimers();
          setScanningDocId(null);
          console.error('ECG poll error:', pollErr);
        }
      }, 3000);
      scanTimersRef.current.pollInterval = pollInterval;
      
      const hardTimeout = setTimeout(() => {
        clearScanTimers();
        setScanningDocId(null);
         const timeoutResult = {
           status: 'timeout',
           doc_id: activeDoc.id,
           prediction: 'Timed out',
           confidence: 0,
           ocr_text: 'ECG scan timed out after 3 minutes. Try again, or check backend logs for the job.',
           xai_analysis: 'ECG scan job did not return results within the UI timeout window.',
           markers: {}
         };
         setScanResult(timeoutResult);
         setEnableAi(true);
         try { localStorage.setItem(scanCacheKey(activeDoc.id), JSON.stringify(timeoutResult)); } catch {}
      }, 180000);
      scanTimersRef.current.hardTimeout = hardTimeout;

    } catch (err) {
      console.error('ECG start error:', err);
      clearScanTimers();
      setScanningDocId(null);
      setScanPhase(0);
    }
  };

  const handleReprocess = async () => {
    if (!activeDoc) return;
    setScanningDocId(activeDoc.id);
    
    try {
      const token = localStorage.getItem('hospital_token');
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`/api/v1/patients/${uid}/documents/reprocess/${activeDoc.id}`, {}, { headers });
      
      // Poll every 5 seconds, up to 36 times (180s)
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        try {
            attempts++;
            const res = await axios.get(`/api/v1/patients/${uid}/documents`, { headers });
            const updatedDoc = res.data.find((d: any) => d.id === activeDoc.id);
            
            // Check if it's updated (doesn't have the old error)
             if (updatedDoc && (!updatedDoc.extracted_text?.includes('[OCR') || attempts >= 36)) {
                 setDocs(res.data);
                 clearInterval(pollInterval);
                 setScanningDocId(null);
             }
        } catch (e) {
            if (attempts >= 36) {
                clearInterval(pollInterval);
                setScanningDocId(null);
            }
        }
      }, 5000);
      
    } catch (err) {
      console.error('Reprocess error:', err);
      setScanningDocId(null);
    }
  };

  const handleNext = () => {
    if (activeIndex < currentCategoryDocs.length - 1) setActiveIndex(activeIndex + 1);
  };

  const handlePrev = () => {
    if (activeIndex > 0) setActiveIndex(activeIndex - 1);
  };

  const switchCategory = (cat: string) => {
    setActiveCategory(cat);
    setActiveIndex(0);
    setEnableAi(false);
    setScanResult(null);
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-10 h-10 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
    </div>
  );

  // ── Use CATEGORY as the definitive source of truth ──────────────────────
  // The category was explicitly set by the user during upload, or by the smart organizer.
  // We only fall back to filename heuristics if category is missing/unknown.
  const docCategory = activeDoc?.category || 'General_Records';

  const isMri = docCategory === 'Radiology_Scans' || (
    activeDoc && !docCategory && (
      activeDoc.file_name.toLowerCase().includes('mri') ||
      activeDoc.file_name.toLowerCase().includes('ct') ||
      activeDoc.file_name.toLowerCase().includes('scan')
    )
  );

  const isEcg = docCategory === 'ECG_Signals' || (
    activeDoc && !docCategory && (
      activeDoc.file_name.toLowerCase().includes('ecg') ||
      activeDoc.file_name.toLowerCase().includes('ekg')
    )
  );

  const isLabReport = docCategory === 'Laboratory_Tests';
  const isClinicalReport = docCategory === 'Clinical_Reports';
  const isDocNotes = docCategory === 'Doctor_Notes';
  const isReport = activeDoc && !isMri && !isEcg && !isDocNotes;
  
  const isDocScanning = scanningDocId === activeDoc?.id;

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col font-sans h-screen overflow-hidden">
      
      {/* Header */}
      <nav className="h-20 border-b border-white/10 flex items-center justify-between px-8 bg-slate-950 shrink-0">
        <div className="flex items-center gap-6">
          <button onClick={() => router.push(`/patient/${uid}`)} className="text-slate-400 hover:text-white transition-colors flex items-center gap-2 font-bold text-sm">
            <ArrowLeft size={16} /> Dashboard Loop
          </button>
          <div className="w-px h-6 bg-white/10"></div>
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 bg-blue-600/20 text-blue-400 rounded-lg flex items-center justify-center">
               <LayoutTemplate size={20} />
             </div>
             <div>
               <h1 className="font-bold tracking-tight leading-none text-lg">Radiology & Clinical Vault</h1>
               <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Patient: {uid}</span>
             </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
           <Link href={`/patient/${uid}?openCockpit=1`} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-600/20 transition-all flex items-center gap-2">
             <Zap size={16} /> AI Diagnostic Cockpit
           </Link>
        </div>
      </nav>

      {/* Main Vault Content */}
      <main className="flex-1 flex overflow-hidden">
        
        {docs.length === 0 ? (
           <div className="w-full flex flex-col items-center justify-center text-slate-500">
             <FolderOpen size={64} className="mb-4 opacity-20" />
             <h2 className="text-xl font-bold text-slate-400">Empty Clinical Directory</h2>
             <p className="text-sm mt-2">No deep learning scans or clinical reports found.</p>
           </div>
        ) : (
           <>
              {/* PANE 1: Directory Tree (Folders) */}
              <div className="w-64 border-r border-slate-800 bg-slate-950 shrink-0 flex flex-col overflow-y-auto custom-scrollbar">
                 <div className="h-16 flex items-center px-6 border-b border-white/5 bg-slate-900/50 shrink-0 sticky top-0 z-10">
                    <h3 className="font-black tracking-widest uppercase text-xs text-slate-400">Clinical Albums</h3>
                 </div>
                 <div className="p-4 space-y-2">
                    {categories.map((cat, i) => (
                       <button 
                         key={i} 
                         onClick={() => switchCategory(cat)}
                         className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-left ${activeCategory === cat ? 'bg-blue-600/10 border-blue-600/30 border text-blue-400 font-bold' : 'text-slate-300 hover:bg-white/5 border border-transparent'}`}
                       >
                         {activeCategory === cat ? <FolderOpen size={18} /> : <Folder size={18} />}
                         <div className="flex flex-col flex-1 overflow-hidden">
                           <span className="text-sm truncate leading-tight">{cat.replace(/_/g, ' ')}</span>
                           <span className="text-[10px] uppercase tracking-widest text-slate-500 mt-0.5">{groupedDocs[cat].length} Files</span>
                         </div>
                       </button>
                    ))}
                 </div>
              </div>

              {/* PANE 2: Image Viewer Sequence (MRI Slices) */}
              <div className="flex-1 border-r border-white/10 flex flex-col bg-black relative">
                 
                 <div className="h-16 flex items-center justify-between px-6 border-b border-white/5 bg-slate-900/50 sticky top-0 z-10 shrink-0">
                    <span className="text-sm font-bold text-slate-300 truncate max-w-[50%] flex items-center gap-3">
                      {activeDoc?.file_name} <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-1 rounded">SEQUENCE SLICE</span>
                    </span>
                    
                    <div className="flex items-center gap-4">
                      {/* MRI SMART SCAN BUTTON */}
                      {isMri && (
                        <button 
                          onClick={handleStartScan} 
                          disabled={scanningDocId !== null}
                          className={`flex items-center gap-2 text-[10px] px-4 py-2 rounded-full uppercase tracking-widest font-black transition-all ${isDocScanning ? 'bg-blue-900/50 text-blue-400 border border-blue-500/50' : 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_15px_rgba(37,99,235,0.4)]'}`}
                        >
                          <ScanEye size={14} className={isDocScanning ? 'animate-spin' : ''}/> {isDocScanning ? 'Analyzing Neural Patterns...' : 'Run Smart AI Scan'}
                        </button>
                      )}

                      {/* ECG SCAN BUTTON */}
                      {isEcg && (
                        <button 
                          onClick={handleEcgScan} 
                          disabled={scanningDocId !== null}
                          className={`flex items-center gap-2 text-[10px] px-4 py-2 rounded-full uppercase tracking-widest font-black transition-all ${isDocScanning ? 'bg-red-900/50 text-red-400 border border-red-500/50' : 'bg-red-600 hover:bg-red-500 text-white shadow-[0_0_15px_rgba(220,38,38,0.4)]'}`}
                        >
                          <Activity size={14} className={isDocScanning ? 'animate-spin' : ''}/> {isDocScanning ? 'Digitizing ECG Grid...' : 'Run ECG AI Analysis'}
                        </button>
                      )}

                      {/* DOCTOR NOTES HANDWRITING BUTTON */}
                      {isDocNotes && (
                        <button 
                          onClick={handleReprocess}
                          disabled={scanningDocId !== null}
                          className="flex items-center gap-2 text-[10px] px-4 py-2 rounded-full uppercase tracking-widest font-black transition-all bg-amber-500 hover:bg-amber-400 text-white shadow-[0_0_15px_rgba(245,158,11,0.4)]"
                        >
                          <PenLine size={14} /> Analyze Handwriting
                        </button>
                      )}

                      {/* SMART REPORT ANALYZER BUTTON — label changes by category */}
                      {isReport && (
                        <button 
                          onClick={handleReprocess} 
                          disabled={scanningDocId !== null}
                          className={`flex items-center gap-2 text-[10px] px-4 py-2 rounded-full uppercase tracking-widest font-black transition-all text-white ${isLabReport ? 'bg-purple-600 hover:bg-purple-500 shadow-[0_0_15px_rgba(147,51,234,0.4)]' : isClinicalReport ? 'bg-teal-600 hover:bg-teal-500 shadow-[0_0_15px_rgba(20,184,166,0.4)]' : 'bg-emerald-600 hover:bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.4)]'}`}
                        >
                          <FileText size={14} /> 
                          {isLabReport ? 'Analyze Lab Results' : isClinicalReport ? 'Analyze Clinical Report' : 'Smart Report Analyzer'}
                        </button>
                      )}
                      
                      {enableAi && (
                         <button 
                           onClick={() => {
                             clearScanTimers();
                             setEnableAi(false);
                             setScanResult(null);
                             setScanPhase(0);
                             setScanningDocId(null);
                             if (activeDoc?.id) {
                               try { localStorage.removeItem(scanCacheKey(activeDoc.id)); } catch {}
                             }
                           }} 
                           className="flex items-center gap-2 text-[10px] px-3 py-1.5 bg-red-500/10 border border-red-500/20 text-red-500 rounded-full uppercase tracking-widest font-black"
                         >
                          Reset
                        </button>
                      )}
                      <a href={`/api/v1/patients/${uid}/documents/${activeDoc?.id}`} target="_blank" className="text-blue-400 hover:text-blue-300 p-2 bg-white/5 rounded-full transition-colors"><Download size={14} /></a>
                    </div>
                 </div>

                 <div className="flex-1 overflow-auto flex items-start justify-center p-8 custom-scrollbar relative">
                    {activeDoc && (
                      <div className={`relative vault-anim transition-all duration-500 ${isDocScanning ? 'scale-[0.98] outline-[6px] outline-blue-600 outline rounded-sm shadow-[0_0_100px_rgba(37,99,235,0.6)]' : ''}`}>
                        
                        {/* Scanning Line Animation */}
                        {isDocScanning && (
                           <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-blue-400 to-transparent shadow-[0_0_20px_#3b82f6] z-50 animate-[scan-line_2s_linear_infinite]"></div>
                        )}

                         <img 
                          key={activeDoc.id}
                          src={enableAi && scanResult ? (vizMode === 'heatmap' ? (scanResult.heatmap_image || scanResult.detection_image) : scanResult.detection_image) : `/api/v1/patients/${uid}/documents/${activeDoc.id}`} 
                          alt={activeDoc.file_name}
                          className={`max-w-full h-auto object-contain rounded drop-shadow-2xl transition-all duration-700 ${isDocScanning ? 'brightness-50 grayscale' : 'brightness-100 grayscale-0'}`}
                        />
                        
                        {/* AI Detection HUD */}
                        {enableAi && scanResult && (
                           <>
                              <div className="absolute inset-0 z-20 pointer-events-none ring-4 ring-red-500 ring-inset animate-pulse">
                                 <div className="absolute top-4 right-4 bg-red-600 text-white px-3 py-1 rounded text-xs font-black uppercase tracking-tighter shadow-lg">
                                    {scanResult.prediction} ({(scanResult.confidence * 100).toFixed(1)}%)
                                 </div>
                              </div>
                              
                              {/* Visualization Toggler */}
                              {!isEcg && (
                                <div className="absolute bottom-4 right-4 z-30 flex bg-black/80 backdrop-blur-md rounded-lg overflow-hidden border border-white/20 shadow-2xl">
                                   <button 
                                     onClick={() => setVizMode('heatmap')} 
                                     className={`px-3 py-1.5 text-[10px] font-black uppercase tracking-widest transition-all ${vizMode === 'heatmap' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
                                   >
                                     Heatmap
                                   </button>
                                   <button 
                                     onClick={() => setVizMode('detection')} 
                                     className={`px-3 py-1.5 text-[10px] font-black uppercase tracking-widest transition-all ${vizMode === 'detection' ? 'bg-red-600 text-white' : 'text-slate-400 hover:text-white'}`}
                                   >
                                     Detections
                                   </button>
                                </div>
                              )}
                           </>
                        )}
                      </div>
                    )}
                 </div>

                 {/* Internal Album Pagination */}
                 {currentCategoryDocs.length > 1 && (
                    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-slate-900/80 backdrop-blur-md border border-white/10 rounded-full px-4 py-2 flex items-center gap-6 shadow-2xl z-20">
                       <button 
                         onClick={handlePrev} 
                         disabled={activeIndex === 0}
                         className={`p-2 rounded-full transition-colors ${activeIndex === 0 ? 'text-slate-600 cursor-not-allowed' : 'text-slate-200 hover:bg-white/10 hover:text-white'}`}
                       >
                         <ChevronLeft size={24} />
                       </button>
                       <span className="text-sm font-mono font-bold text-slate-400 w-24 text-center">
                          {activeIndex + 1} <span className="text-slate-600">/</span> {currentCategoryDocs.length}
                       </span>
                       <button 
                         onClick={handleNext} 
                         disabled={activeIndex === currentCategoryDocs.length - 1}
                         className={`p-2 rounded-full transition-colors ${activeIndex === currentCategoryDocs.length - 1 ? 'text-slate-600 cursor-not-allowed' : 'text-slate-200 hover:bg-white/10 hover:text-white'}`}
                       >
                         <ChevronRight size={24} />
                       </button>
                    </div>
                 )}
              </div>

              {/* PANE 3: Deep NLP Text/Data Reference */}
              <div className="w-80 lg:w-96 flex flex-col bg-slate-900 shrink-0">
                 
                 <div className="h-16 flex items-center px-8 border-b border-white/10 bg-slate-800/50 shrink-0">
                    <h3 className={`font-black tracking-widest uppercase text-xs flex items-center gap-3 ${enableAi ? 'text-red-400' : 'text-blue-400'}`}>
                       {enableAi ? <Activity size={16} className="animate-pulse" /> : <FileText size={16} />}
                       {enableAi ? 'Smart Diagnostic Insights' : 'Clinical NLP Extraction'}
                    </h3>
                 </div>

                 <div className="flex-1 p-8 overflow-y-auto custom-scrollbar bg-slate-900/50 vault-anim">
                   
                    {isDocScanning ? (
                       <div className="flex flex-col h-full text-slate-300 p-2 space-y-8 animate-in fade-in duration-500">
                          <div className="flex flex-col items-center justify-center border-b border-white/10 pb-6">
                             <BrainCircuit size={48} className="text-blue-500 animate-pulse mb-3" />
                             <span className="font-black uppercase tracking-widest text-xs text-blue-400">Deep Diagnostic Sequence</span>
                          </div>
                          
                          <div className="space-y-6 font-mono text-xs pl-2">
                             <div className={`flex items-center gap-4 transition-opacity duration-500 ${scanPhase >= 1 ? 'opacity-100' : 'opacity-20'}`}>
                                <div className={`w-2 h-2 rounded-full shrink-0 ${scanPhase > 1 ? 'bg-green-500' : 'bg-blue-500 animate-pulse shadow-[0_0_10px_#3b82f6]'}`}></div>
                                <span className={scanPhase === 1 ? 'text-white' : 'text-slate-400'}>1. Normalizing Image Matrix (CLAHE)...</span>
                             </div>
                             
                             <div className={`flex items-center gap-4 transition-opacity duration-500 ${scanPhase >= 2 ? 'opacity-100' : 'opacity-20'}`}>
                                <div className={`w-2 h-2 rounded-full shrink-0 ${scanPhase > 2 ? 'bg-green-500' : (scanPhase === 2 ? 'bg-blue-500 animate-pulse shadow-[0_0_10px_#3b82f6]' : 'bg-slate-700')}`}></div>
                                <span className={scanPhase === 2 ? 'text-white' : 'text-slate-400'}>2. Morphological Grid Slicing...</span>
                             </div>
                             
                             <div className={`flex items-center gap-4 transition-opacity duration-500 ${scanPhase >= 3 ? 'opacity-100' : 'opacity-20'}`}>
                                <div className={`w-2 h-2 rounded-full shrink-0 ${scanPhase > 3 ? 'bg-green-500' : (scanPhase === 3 ? 'bg-blue-500 animate-pulse shadow-[0_0_10px_#3b82f6]' : 'bg-slate-700')}`}></div>
                                <span className={scanPhase === 3 ? 'text-white' : 'text-slate-400'}>3. FastAI Multi-Class Inference...</span>
                             </div>
                             
                             <div className={`flex items-center gap-4 transition-opacity duration-500 ${scanPhase >= 4 ? 'opacity-100' : 'opacity-20'}`}>
                                <div className={`w-2 h-2 rounded-full shrink-0 ${scanPhase > 4 ? 'bg-green-500' : (scanPhase === 4 ? 'bg-blue-500 animate-pulse shadow-[0_0_10px_#3b82f6]' : 'bg-slate-700')}`}></div>
                                <span className={scanPhase === 4 ? 'text-white' : 'text-slate-400'}>4. Plotting Explainable Contours...</span>
                             </div>
                          </div>
                       </div>
                    ) : enableAi && scanResult ? (
                       <div className="animate-in fade-in slide-in-from-right-4 duration-500 overflow-x-hidden">
                         <div className="space-y-6">
                            
                            <div>
                               <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 ml-1">OCR Clinical Metadata</h4>
                               <div className="bg-black/60 border border-white/5 p-4 rounded-xl text-[10px] font-mono text-blue-300 leading-relaxed max-h-32 overflow-y-auto custom-scrollbar shrink-0 shadow-inner">
                                  {scanResult.ocr_text || "No legible text extracted."}
                               </div>
                            </div>

                            <div>
                               <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 ml-1">Neural Landmark Analysis</h4>
                               {Object.keys(scanResult.markers || {}).length > 0 ? (
                                 <div className="grid grid-cols-2 gap-2">
                                     {Object.entries(scanResult.markers || {}).map(([k, v]: [string, any]) => (
                                       <div key={k} className="bg-slate-800/80 border border-white/5 p-3 rounded-lg flex flex-col">
                                           <span className="text-[9px] uppercase font-bold text-slate-500 truncate">{k.replace(/_/g, ' ')}</span>
                                           <span className="text-[10px] font-black text-white mt-1">{String(v)}</span>
                                       </div>
                                     ))}
                                 </div>
                               ) : (
                                 <div className="bg-slate-900/50 border border-white/5 p-4 rounded-xl text-[10px] font-medium text-slate-500 italic text-center">
                                   Landmark extraction in progress or unavailable for this scan.
                                 </div>
                               )}
                            </div>

                            <div>
                               <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 ml-1">Radiological Impression</h4>
                               <div className="bg-red-500/10 border border-red-500/20 p-5 rounded-2xl relative overflow-hidden group">
                                  <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:scale-110 transition-transform">
                                    <ShieldAlert size={48} className="text-red-500" />
                                  </div>
                                  <p className="text-xs text-red-100/90 leading-relaxed font-semibold relative z-10 italic">
                                     "{scanResult.xai_analysis}"
                                  </p>
                               </div>
                            </div>

                            <div className="p-5 bg-gradient-to-br from-slate-800/80 to-slate-900 border border-white/10 rounded-2xl shadow-xl">
                               <div className="flex items-center justify-between mb-4">
                                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Diagnostic Confidence</span>
                                  <span className={`text-[9px] font-black px-2 py-0.5 rounded shadow-sm ${scanResult.prediction?.includes('Yes') ? 'bg-red-500/20 text-red-500' : 'bg-green-500/20 text-green-500'}`}>
                                    {scanResult.prediction?.includes('Yes') ? 'ALERT' : 'NOMINAL'}
                                  </span>
                                </div>
                                <div className="text-2xl font-black text-white tracking-tight">{scanResult.prediction}</div>
                                <div className="mt-4 flex items-center gap-3">
                                   <div className="flex-1 h-2 bg-black/40 rounded-full overflow-hidden border border-white/5">
                                      <div 
                                        className={`h-full transition-all duration-1000 ${scanResult.prediction?.includes('Yes') ? 'bg-red-500' : 'bg-blue-500'}`} 
                                        style={{width: `${scanResult.confidence * 100}%`}}
                                      ></div>
                                   </div>
                                   <span className="text-xs font-black text-slate-300">{(scanResult.confidence * 100).toFixed(1)}%</span>
                                </div>
                            </div>

                         </div>

                         <div className="mt-10 border-t border-white/10 pt-6">
                           <button onClick={() => window.location.href=`/patient/${uid}?openCockpit=1`} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-[10px] uppercase tracking-[0.2em] py-4 rounded-2xl shadow-2xl shadow-blue-500/30 transition-all flex items-center justify-center gap-2 active:scale-[0.98]">
                             <Zap size={16} fill="currentColor" /> Initialize Causal Sandbox
                           </button>
                         </div>
                       </div>
                    ) : (
                      <>
                        {activeDoc?.extracted_text && activeDoc?.extracted_text !== '' ? (
                           <div className="text-slate-300 text-xs leading-relaxed whitespace-pre-wrap font-mono relative">
                              {activeDoc.extracted_text}
                           </div>
                        ) : (
                           <div className="h-full flex flex-col items-center justify-center text-slate-600 border-2 border-dashed border-white/5 rounded-2xl p-8 text-center bg-black/20">
                             <FileText size={48} className="mb-4 opacity-20" />
                             <span className="text-sm font-bold text-slate-400 mb-1">Metadata Unavailable</span>
                             <span className="text-[10px] font-medium max-w-[200px] leading-relaxed">Select an MRI scan and click "Run Smart AI Scan" to initialize deep analysis.</span>
                           </div>
                        )}
                      </>
                    )}

                 </div>

              </div>
           </>
        )}

      </main>

      <style jsx global>{`
        @keyframes scan-line {
          0% { top: 0; }
          100% { top: 100%; }
        }
      `}</style>
    </div>
  );
}
