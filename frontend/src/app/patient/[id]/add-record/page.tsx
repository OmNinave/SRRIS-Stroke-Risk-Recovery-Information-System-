"use client";

import { useState } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, Activity, Calendar, Pill, AlertTriangle, Syringe, Save, UploadCloud
} from 'lucide-react';

export default function AddRecordPage() {
  const { id: uid } = useParams();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('event'); // event, medication, surgery, lab, document
  const [loading, setLoading] = useState(false);

  // Form states
  const [eventData, setEventData] = useState({ title: '', event_date: '', event_type: 'diagnosis', description: '', outcome: '' });
  const [medData, setMedData] = useState({ drug_name: '', dosage: '', frequency: '', start_date: '', is_active: true });
  const [labData, setLabData] = useState({ test_name: '', value: '', unit: '', result_date: '', status: 'normal' });

  // Add Document State
  const [docCategory, setDocCategory] = useState('other');
  const [docFile, setDocFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('hospital_token');
      const headers = { Authorization: `Bearer ${token}` };
      const baseApi = `/api/v1/patients/${uid}`;

      if (activeTab === 'event') await axios.post(`${baseApi}/events`, eventData, { headers });
      if (activeTab === 'medication') await axios.post(`${baseApi}/medications`, medData, { headers });
      if (activeTab === 'lab') await axios.post(`${baseApi}/labs`, labData, { headers });
      if (activeTab === 'document' && docFile) {
        const formData = new FormData();
        formData.append('file', docFile);
        formData.append('category', docCategory);
        await axios.post(`${baseApi}/documents/upload?category=${docCategory}`, formData, { 
          headers: { ...headers, 'Content-Type': 'multipart/form-data' } 
        });
      }

      router.push(`/patient/${uid}`);
    } catch (err: any) {
      alert("Error saving record: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <Link href={`/patient/${uid}`} className="text-slate-500 hover:text-slate-900 font-bold mb-8 flex items-center gap-2">
           <ArrowLeft size={18} /> Back to Dossier
        </Link>
        
        <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-xl shadow-slate-200/50">
           <div className="flex border-b border-slate-200">
             {[
               { id: 'event', icon: Calendar, label: 'Clinical Event' },
               { id: 'medication', icon: Pill, label: 'Medication' },
               { id: 'lab', icon: Activity, label: 'Lab Result' },
               { id: 'document', icon: UploadCloud, label: 'Upload OCR Document' }
             ].map(t => (
               <button 
                 key={t.id} 
                 onClick={() => setActiveTab(t.id)}
                 className={`flex-1 py-4 flex items-center justify-center gap-2 font-bold text-sm transition-colors border-b-2
                  ${activeTab === t.id ? 'bg-blue-50 text-blue-600 border-blue-600' : 'bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900 border-transparent'}
                 `}
               >
                 <t.icon size={16} /> {t.label}
               </button>
             ))}
           </div>

           <form onSubmit={handleSubmit} className="p-8">
              {activeTab === 'event' && (
                <div className="space-y-6">
                  <h3 className="text-lg font-black text-slate-900 mb-6">Log New Clinical Event</h3>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Event Title</label>
                    <input required value={eventData.title} onChange={e => setEventData({...eventData, title: e.target.value})} type="text" className="w-full input-clinical border border-slate-200 rounded-xl px-4 py-3" placeholder="e.g. Diagnosed with Hypertension" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Date</label>
                      <input required value={eventData.event_date} onChange={e => setEventData({...eventData, event_date: e.target.value})} type="datetime-local" className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Type</label>
                      <select value={eventData.event_type} onChange={e => setEventData({...eventData, event_type: e.target.value})} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900">
                        <option value="diagnosis">Diagnosis</option>
                        <option value="stroke_event">Stroke Event</option>
                        <option value="follow_up_missed">Missed Follow-up</option>
                        <option value="general">General Visit</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Clinical Details</label>
                    <textarea value={eventData.description} onChange={e => setEventData({...eventData, description: e.target.value})} rows={3} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" placeholder="Extensive background..."></textarea>
                  </div>
                </div>
              )}

              {activeTab === 'medication' && (
                <div className="space-y-6">
                  <h3 className="text-lg font-black text-slate-900 mb-6 flex items-center gap-2"><Pill size={20} className="text-blue-600"/> Prescribe Medication</h3>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Drug Name</label>
                    <input required value={medData.drug_name} onChange={e => setMedData({...medData, drug_name: e.target.value})} type="text" className="w-full input-clinical border border-slate-200 rounded-xl px-4 py-3 text-slate-900" placeholder="e.g. Apixaban" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Dosage</label>
                      <input required value={medData.dosage} onChange={e => setMedData({...medData, dosage: e.target.value})} type="text" className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" placeholder="e.g. 5mg" />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Start Date</label>
                      <input required value={medData.start_date} onChange={e => setMedData({...medData, start_date: e.target.value})} type="datetime-local" className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'lab' && (
                <div className="space-y-6">
                  <h3 className="text-lg font-black text-slate-900 mb-6 flex items-center gap-2"><Activity size={20} className="text-emerald-500"/> Log Lab Result</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Test Name</label>
                      <input required value={labData.test_name} onChange={e => setLabData({...labData, test_name: e.target.value})} type="text" className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" placeholder="e.g. systolic_bp" />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Date</label>
                      <input required value={labData.result_date} onChange={e => setLabData({...labData, result_date: e.target.value})} type="datetime-local" className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Value</label>
                      <input required value={labData.value} onChange={e => setLabData({...labData, value: e.target.value})} type="text" className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900" placeholder="e.g. 140" />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Status</label>
                      <select value={labData.status} onChange={e => setLabData({...labData, status: e.target.value})} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900">
                        <option value="normal">Normal</option>
                        <option value="abnormal">Abnormal</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'document' && (
                <div className="space-y-6">
                  <h3 className="text-lg font-black text-slate-900 mb-6 flex items-center gap-2"><UploadCloud size={20} className="text-blue-500"/> Organized Document Ingestion</h3>
                  <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl flex gap-3 text-blue-800 text-sm font-medium">
                     <AlertTriangle className="text-blue-600 shrink-0 mt-0.5" size={18} />
                     Select a clinical category to automatically route this document to its specialized AI diagnostic vault.
                  </div>
                  
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Clinical Category</label>
                    <select 
                      value={docCategory} 
                      onChange={e => setDocCategory(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900 bg-white font-bold"
                    >
                      <option value="General_Records">General Records</option>
                      <option value="Radiology_Scans">Radiology Scans (MRI/CT)</option>
                      <option value="ECG_Signals">ECG Signal Reports</option>
                      <option value="Clinical_Reports">Clinical Reports (Admission/Discharge)</option>
                      <option value="Laboratory_Tests">Laboratory & Blood Tests</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Select File (PDF, PNG, JPG)</label>
                    <input required type="file" onChange={e => setDocFile(e.target.files?.[0] || null)} className="w-full border border-slate-200 rounded-xl px-4 py-8 text-slate-900 bg-slate-50 cursor-pointer font-medium" />
                  </div>
                </div>
              )}

              <div className="mt-10 pt-6 border-t border-slate-100 flex justify-end">
                <button disabled={loading} type="submit" className="bg-blue-600 hover:bg-blue-700 text-white font-bold tracking-tight px-10 py-3 rounded-xl shadow-lg shadow-blue-600/20 active:scale-95 transition-all flex items-center gap-2">
                  {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Save size={18} />}
                  Save Record
                </button>
              </div>
           </form>
        </div>
      </div>
    </div>
  );
}
