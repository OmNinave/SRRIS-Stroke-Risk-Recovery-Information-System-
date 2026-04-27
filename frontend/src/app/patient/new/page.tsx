"use client";

import { useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, UserPlus, UploadCloud, X, FileText, CheckCircle } from 'lucide-react';

export default function NewPatientRegistration() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [successUid, setSuccessUid] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    full_name: '',
    date_of_birth: '',
    gender: 'Male',
    blood_type: 'O+',
    phone: '',
    ward_area: 'Neurology ICU',
    bed_no: '',
    primary_diagnosis: 'Acute Ischemic Stroke'
  });

  const [files, setFiles] = useState<{file: File, category: string}[]>([]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files).map(f => ({
        file: f,
        category: 'General_Records'
      }));
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('hospital_token');
      if (!token) return router.push('/');
      const headers = { Authorization: `Bearer ${token}` };

      // 1. Register Patient
      const res = await axios.post('/api/v1/patients/register', formData, { headers });
      const newUid = res.data.patient_uid;

      // 2. Batch Upload Documents
      if (files.length > 0) {
        for (const fObj of files) {
          const formPayload = new FormData();
          formPayload.append('file', fObj.file);
          formPayload.append('category', fObj.category);
          await axios.post(`/api/v1/patients/${newUid}/documents/upload?category=${fObj.category}`, formPayload, {
            headers: {
              ...headers,
              'Content-Type': 'multipart/form-data'
            }
          });
        }
      }

      setSuccessUid(newUid);

    } catch (err) {
      console.error(err);
      alert('Failed to register patient or upload documents.');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  if (successUid) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-8">
         <div className="bg-white p-12 rounded-3xl shadow-xl shadow-blue-900/5 flex flex-col items-center text-center max-w-lg border border-slate-200">
            <div className="w-24 h-24 bg-green-50 text-green-500 rounded-full flex flex-col items-center justify-center mb-6">
               <CheckCircle size={48} />
            </div>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight leading-none mb-4">Patient Registered Successfully!</h2>
            <p className="text-slate-500 font-medium mb-8">
               Identity <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded">{successUid}</span> has been completely initialized. Optical Scan Background tasks have successfully started processing their documents via AI.
            </p>
            <button onClick={() => router.push(`/patient/${successUid}`)} className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-xl font-bold shadow-lg shadow-blue-500/20 w-full transition-all text-lg">
               Initialize Scientific Dossier
            </button>
         </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col pb-20">
      
      {/* Header */}
      <nav className="h-24 bg-white border-b border-slate-200 px-8 flex items-center justify-between shadow-sm sticky top-0 z-50">
         <div className="flex items-center gap-6">
           <Link href="/directory" className="text-slate-400 hover:text-slate-900 transition-colors flex items-center gap-2 font-bold text-sm">
             <ArrowLeft size={16} /> Cancel Registry
           </Link>
           <div className="w-px h-8 bg-slate-200"></div>
           <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-600/10 text-blue-600 rounded-xl flex items-center justify-center">
                <UserPlus size={24} />
              </div>
              <div>
                <h1 className="font-black text-slate-900 tracking-tight text-xl leading-none mb-1">New Patient Medical Registration</h1>
                <p className="text-[10px] uppercase font-black tracking-widest text-slate-400">Secure Intake Pipeline</p>
              </div>
           </div>
         </div>
         <button onClick={handleSubmit} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-8 py-3 rounded-xl font-bold text-sm shadow-xl shadow-blue-600/20 transition-all flex items-center gap-2">
            {loading ? <div className="w-4 h-4 rounded-full border-2 border-white/20 border-t-white animate-spin"></div> : <CheckCircle size={18}/>}
            {loading ? "Synthesizing Registry..." : "Finalize Registration & Scan"}
         </button>
      </nav>

      <main className="flex-1 max-w-5xl mx-auto w-full pt-10 px-4 grid grid-cols-1 lg:grid-cols-5 gap-8">
         
         <div className="lg:col-span-3 space-y-8">
            <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm flex flex-col">
               <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">Identity Details</h3>
               <div className="grid grid-cols-2 gap-6">
                  <div className="col-span-2">
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Legal Full Name</label>
                     <input type="text" value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none" required placeholder="e.g. John Doe"/>
                  </div>
                  <div>
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Date of Birth (YYYY-MM-DD)</label>
                     <input type="date" value={formData.date_of_birth} onChange={e => setFormData({...formData, date_of_birth: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none" required/>
                  </div>
                  <div>
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Gender</label>
                     <select value={formData.gender} onChange={e => setFormData({...formData, gender: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none">
                        <option>Male</option><option>Female</option><option>Other</option>
                     </select>
                  </div>
                  <div>
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Blood Type</label>
                     <select value={formData.blood_type} onChange={e => setFormData({...formData, blood_type: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none">
                        <option>O+</option><option>O-</option><option>A+</option><option>A-</option><option>B+</option><option>B-</option><option>AB+</option><option>AB-</option><option>Unknown</option>
                     </select>
                  </div>
               </div>
            </div>

            <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm flex flex-col">
               <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">Triage & Admission Rules</h3>
               <div className="grid grid-cols-2 gap-6">
                  <div>
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Ward Location</label>
                     <input type="text" value={formData.ward_area} onChange={e => setFormData({...formData, ward_area: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none"/>
                  </div>
                  <div>
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Bed No.</label>
                     <input type="text" value={formData.bed_no} onChange={e => setFormData({...formData, bed_no: e.target.value})} placeholder="e.g. Bed-14" className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none"/>
                  </div>
                  <div className="col-span-2">
                     <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Primary Preliminary Diagnosis</label>
                     <input type="text" value={formData.primary_diagnosis} onChange={e => setFormData({...formData, primary_diagnosis: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-600 focus:outline-none"/>
                  </div>
               </div>
            </div>
         </div>

         <div className="lg:col-span-2 space-y-8">
            <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm flex flex-col h-full">
               <h3 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">Batch Clinical Up-link</h3>
               <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest leading-relaxed mb-6">Drag and drop raw medical forms (JPG, PNG, PDF) here. The optical engines will automatically rename the files based on deeply parsed dates and lab findings upon Registration.</p>
               
               <label 
                 onDragOver={handleDragOver}
                 onDrop={handleDrop}
                 className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-blue-200 bg-blue-50/50 hover:bg-blue-50 rounded-2xl cursor-pointer transition-colors group"
               >
                 <div className="w-16 h-16 rounded-full bg-white text-blue-500 shadow-sm flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                   <UploadCloud size={32} />
                 </div>
                 <span className="font-bold text-blue-600 tracking-tight text-center">Click or Drag Files Here</span>
                 <span className="text-xs text-blue-400 mt-2 text-center font-medium px-4">Files will be asynchronously processed via AI.</span>
                 <input type="file" multiple className="hidden" onChange={e => {
                   if (e.target.files) {
                     const newFiles = Array.from(e.target.files).map(f => ({
                       file: f,
                       category: 'General_Records'
                     }));
                     setFiles(prev => [...prev, ...newFiles]);
                   }
                 }}/>
               </label>
               
               <div className="flex-1 overflow-y-auto mt-6 space-y-4 custom-scrollbar">
                  {files.map((fObj, i) => (
                     <div key={i} className="flex flex-col p-4 bg-slate-50 border border-slate-200 rounded-2xl gap-3">
                        <div className="flex items-center justify-between">
                           <div className="flex items-center gap-3 overflow-hidden">
                              <FileText size={18} className="text-blue-500 shrink-0" />
                              <span className="text-xs font-bold text-slate-900 truncate">{fObj.file.name}</span>
                           </div>
                           <button onClick={() => removeFile(i)} className="p-2 text-slate-400 hover:text-red-500 rounded-lg shrink-0 transition-colors">
                              <X size={16} />
                           </button>
                        </div>
                        <div className="flex items-center gap-3">
                           <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 shrink-0">Category:</span>
                           <select 
                             value={fObj.category}
                             onChange={(e) => {
                               const newFiles = [...files];
                               newFiles[i].category = e.target.value;
                               setFiles(newFiles);
                             }}
                             className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-[10px] font-bold text-slate-700 outline-none focus:ring-2 focus:ring-blue-600"
                           >
                             <option value="General_Records">General Records</option>
                             <option value="Radiology_Scans">Radiology Scans (MRI/CT)</option>
                             <option value="ECG_Signals">ECG Signal Reports</option>
                             <option value="Clinical_Reports">Clinical Reports</option>
                             <option value="Laboratory_Tests">Laboratory & Blood Tests</option>
                           </select>
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         </div>

      </main>
    </div>
  );
}
