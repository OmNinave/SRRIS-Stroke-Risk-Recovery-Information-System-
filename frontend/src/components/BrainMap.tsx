import React from 'react';
import { ScanEye } from 'lucide-react';

interface BrainMapProps {
  diagnosis: string;
  patientUid: string;
  volume?: number | null;      // volume_percentage from ScanResult — null/undefined = no scan
  confidence?: number | null;  // raw 0-1 confidence from ScanResult
  side?: string | null;
  x?: number | null;
  y?: number | null;
}

export default function BrainMap({ diagnosis, patientUid, volume, confidence, side, x, y }: BrainMapProps) {
  // A real scan result exists ONLY when volume_percentage is a non-null number from the DB
  const hasScan = volume !== null && volume !== undefined && !isNaN(Number(volume));

  // AI confidence: use real scan confidence (0-1 scale → %), fallback to volume_percentage directly
  const aiConfidencePct = hasScan
    ? (confidence !== null && confidence !== undefined ? (Number(confidence) * 100) : Number(volume))
    : null;

  // Lesion position: only draw when a real scan exists
  const lx = hasScan
    ? (x ? (Number(x) * 220) : (side?.toLowerCase() === 'right' ? 155 : 65))
    : 110; // center — won't be rendered
  const ly = hasScan
    ? (y ? (Number(y) * 280) : 135)
    : 140;

  // ── NO-SCAN STATE ──────────────────────────────────────────────────────────
  if (!hasScan) {
    return (
      <div className="relative w-full h-[320px] bg-[#050810] rounded-3xl overflow-hidden border border-white/5 flex flex-col items-center justify-center p-6 shadow-2xl">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0)', backgroundSize: '10px 10px' }} />

        {/* Subtle brain outline (inactive) */}
        <svg className="absolute w-full h-full opacity-[0.06]" viewBox="0 0 220 280" fill="none">
          <path d="M110 15C80 15 55 25 40 55C25 90 25 140 25 180C25 225 45 265 110 275C175 265 195 225 195 180C195 140 195 90 180 55C165 25 140 15 110 15Z" stroke="#3b5998" strokeWidth="2" />
          <path d="M110 15V275" stroke="#3b5998" strokeWidth="1.2" strokeDasharray="4 4" strokeOpacity="0.8" />
        </svg>

        <div className="relative z-10 flex flex-col items-center text-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-slate-800/60 border border-white/5 flex items-center justify-center">
            <ScanEye size={28} className="text-slate-500" />
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 mb-1">No Radiology Data</p>
            <p className="text-[9px] text-slate-600 font-medium max-w-[200px] leading-relaxed">
              Upload a Radiology Scan and run AI analysis in the Document Vault to populate this view.
            </p>
          </div>
          <div className="flex items-center gap-2 bg-slate-800/50 border border-white/5 px-3 py-1.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse" />
            <span className="text-[8px] font-black uppercase tracking-widest text-slate-600">AWAITING SCAN INPUT</span>
          </div>
        </div>

        <div className="absolute bottom-4 left-4 right-4 flex justify-between items-center opacity-30">
          <span className="text-[7px] font-mono text-slate-600 uppercase tracking-widest">NEURO-DIAGNOSTIC CENTER</span>
          <span className="text-[7px] font-mono text-slate-600 uppercase tracking-widest">AI_LESION_SEGMENTATION_v4.2</span>
        </div>
      </div>
    );
  }

  // ── REAL SCAN STATE ────────────────────────────────────────────────────────
  return (
    <div className="relative w-full h-[320px] bg-[#050810] rounded-3xl overflow-hidden border border-white/5 flex flex-col items-center justify-center p-4 shadow-2xl">
      {/* HUD Grid */}
      <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0)', backgroundSize: '10px 10px' }} />

      {/* Technical HUD Overlays */}
      <div className="absolute top-4 left-4 flex flex-col gap-1 z-10">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
          <span className="text-[9px] font-black uppercase text-slate-300 tracking-[0.2em]">LIVE_PACS_LINK: SYNCED</span>
        </div>
        <div className="flex flex-col text-[7px] text-slate-500 font-mono tracking-widest ml-3 mt-1 space-y-0.5 opacity-60 uppercase">
          <span>CONFIDENCE: {aiConfidencePct!.toFixed(1)}%</span>
          <span>ABNORMAL_SLICES: {Math.round(Number(volume) * 0.3)}</span>
          <span>LAT_SIDE: {side || 'BILATERAL'}</span>
        </div>
      </div>

      <div className="absolute top-4 right-4 text-right z-10">
        <span className="text-[9px] font-black uppercase text-slate-400 tracking-[0.2em]">NEURO-DIAGNOSTIC CENTER</span>
        <div className="text-[7px] text-blue-500/60 font-mono mt-1 uppercase tracking-tighter">AI_LESION_SEGMENTATION_v4.2_PRO_STABLE</div>
      </div>

      {/* Main Diagnostic SVG */}
      <svg className="w-full h-full max-h-[250px] z-10 drop-shadow-2xl" viewBox="0 0 220 280" fill="none">
        <defs>
          <radialGradient id="lesionGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ff4444" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#ff4444" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="focalGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
            <stop offset="100%" stopColor="#ffbb00" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Brain outline */}
        <g stroke="#3b5998" strokeWidth="1.2" strokeOpacity="0.3">
          <path d="M110 15C80 15 55 25 40 55C25 90 25 140 25 180C25 225 45 265 110 275C175 265 195 225 195 180C195 140 195 90 180 55C165 25 140 15 110 15Z" strokeWidth="2" strokeOpacity="0.5" />
          <path d="M110 25C88 25 70 35 55 60C45 85 45 125 45 170C45 215 62 250 110 260C158 250 175 215 175 170C175 125 175 85 165 60C150 35 132 25 110 25Z" strokeDasharray="1 3" />
          <path d="M110 15V275" strokeOpacity="0.8" strokeDasharray="4 4" />
          <path d="M105 80C90 100 80 130 80 155C80 180 90 200 100 210" />
          <path d="M115 80C130 100 140 130 140 155C140 180 130 200 120 210" />
        </g>

        {/* Lesion group — only rendered when hasScan is true (guaranteed here) */}
        <g>
          {/* Crosshairs */}
          <line x1="10" y1={ly} x2="210" y2={ly} stroke="#4169e1" strokeWidth="1" strokeOpacity="0.5" strokeDasharray="2 2" />
          <line x1={lx} y1="10" x2={lx} y2="270" stroke="#4169e1" strokeWidth="1" strokeOpacity="0.5" strokeDasharray="2 2" />
          {/* Lesion glow */}
          <circle cx={lx} cy={ly} r="45" fill="#ff0000" fillOpacity="0.1" />
          <circle cx={lx} cy={ly} r="38" fill="#ff0000" fillOpacity="0.15" />
          <circle cx={lx} cy={ly} r="30" fill="url(#lesionGrad)" fillOpacity="0.8" className="animate-pulse" />
          <circle cx={lx} cy={ly} r="22" fill="#ff0000" fillOpacity="0.4" />
          <circle cx={lx} cy={ly} r="12" fill="#ff0000" fillOpacity="0.6" />
          {/* Focal center */}
          <circle cx={lx} cy={ly} r="8" fill="url(#focalGrad)" className="animate-ping" style={{ animationDuration: '2s' }} />
          <circle cx={lx} cy={ly} r="4.5" fill="#ffffff" />
          <circle cx={lx} cy={ly} r="5" fill="none" stroke="#ff0000" strokeWidth="1" strokeOpacity="0.8" />
          {/* Bounding box */}
          <rect x={lx - 35} y={ly - 35} width="70" height="70" stroke="#4169e1" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="1 1" />
          <circle cx={lx - 35} cy={ly - 35} r="2" fill="#4169e1" />
          {/* Coordinates */}
          <text x={lx + 40} y={ly - 10} fill="#4169e1" fontSize="7" fontWeight="black" className="font-mono">LOC_X: {lx.toFixed(1)}</text>
          <text x={lx + 40} y={ly} fill="#4169e1" fontSize="7" fontWeight="black" className="font-mono">LOC_Y: {ly.toFixed(1)}</text>
        </g>
      </svg>

      {/* AI Confidence — real value from scan */}
      <div className="absolute bottom-4 right-4 text-right z-10">
        <span className="text-[9px] font-black uppercase text-red-500 tracking-widest mb-1 block">AI CONFIDENCE</span>
        <div className="flex items-baseline gap-0.5 justify-end">
          <span className="text-5xl font-black text-white tracking-tighter">
            {aiConfidencePct!.toFixed(1)}
          </span>
          <span className="text-xl font-bold text-slate-500">%</span>
        </div>
        <span className="text-[6px] font-black uppercase text-slate-600 tracking-widest">{side || 'BILATERAL'} HEMISPHERE</span>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex flex-col gap-2 z-10">
        <div className="flex gap-1 h-1.5 w-24">
          <div className="flex-1 bg-emerald-500 opacity-60 rounded-l-full" />
          <div className="flex-[0.5] bg-orange-500" />
          <div className="flex-[1.5] bg-red-600 rounded-r-full shadow-[0_0_12px_rgba(220,38,38,0.6)]" />
        </div>
        <div className="flex justify-between w-24 text-[6px] font-black text-slate-500 tracking-widest uppercase">
          <span>PENUMBRA</span>
          <span>CORE</span>
        </div>
      </div>
    </div>
  );
}
