"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Search, Users, Activity, LogOut, ChevronRight, UserCircle, Bell, Settings, Filter, Plus, RefreshCcw } from 'lucide-react';
import gsap from 'gsap';

export default function DirectoryPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [user, setUser] = useState<{full_name: string, role: string, department?: string} | null>(null);
  const router = useRouter();

  const fetchDirectory = async (showAnimations = true) => {
    const token = localStorage.getItem('hospital_token');
    if (!token) {
      router.push('/');
      return;
    }

    try {
      const config = { headers: { Authorization: `Bearer ${token}` } };
      const [meRes, patRes] = await Promise.all([
        axios.get('/api/v1/auth/me', config),
        axios.get(`/api/v1/patients/search?q=${searchQuery}`, config)
      ]);
      
      setUser(meRes.data);
      setPatients(patRes.data);

      if (showAnimations) {
        gsap.fromTo(".directory-header", { opacity: 0, y: -20 }, { opacity: 1, y: 0, duration: 0.8, ease: "power2.out" });
        setTimeout(() => {
          gsap.fromTo(".patient-card", 
            { opacity: 0, y: 20 }, 
            { opacity: 1, y: 0, stagger: 0.1, duration: 0.8, ease: "power3.out" }
          );
        }, 50);
      }
    } catch (err) {
      localStorage.removeItem('hospital_token');
      router.push('/');
    }
  };

  useEffect(() => {
    fetchDirectory();
    
    const interval = setInterval(() => {
      fetchDirectory(false);
    }, 10000);
    
    return () => clearInterval(interval);
  }, [router, searchQuery]);

  const handleLogout = () => {
    localStorage.removeItem('hospital_token');
    router.push('/');
  };

  if (!user) return (
    <div className="min-h-screen flex flex-col items-center justify-center clinical-gradient text-slate-500 gap-4">
      <div className="w-10 h-10 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
      <span className="font-bold tracking-widest text-[10px] uppercase">Accessing Secure Registry...</span>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <nav className="h-20 border-b border-slate-200 bg-white flex items-center justify-between px-8 relative z-50 shadow-sm">
        <div className="flex items-center gap-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-600/10">
              <Users size={20} />
            </div>
            <div>
              <h1 className="text-slate-900 font-bold tracking-tight text-lg">Hospital Directory</h1>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">Scientific Patient Registry</p>
            </div>
          </div>
          
          <div className="hidden md:flex items-center gap-6">
            <Link href="/directory" className="text-blue-600 text-sm font-bold flex items-center gap-2">
               <Activity size={16} /> Dashboard
            </Link>
            <span className="text-slate-200">|</span>
            <Link href="/patient/new" className="text-blue-600 hover:text-blue-700 text-sm font-bold flex items-center gap-2 transition-colors">
               <Plus size={16} /> Register Patient
            </Link>
            <span className="text-slate-200">|</span>
            <button onClick={() => alert('Emergency protocols initialized...')} className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">Emergency Triage</button>
            <button onClick={() => alert('Accessing departmental shift schedules...')} className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">Departmental Logs</button>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="hidden lg:flex flex-col items-end">
            <span className="text-slate-900 text-sm font-bold leading-none">{user.full_name}</span>
            <span className="text-slate-400 text-[10px] uppercase tracking-widest mt-1 font-bold">{user.role} · {user.department || 'Neurology'}</span>
          </div>
          <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 hover:text-blue-600 transition-colors cursor-pointer">
            <UserCircle size={24} />
          </div>
          <button onClick={handleLogout} className="w-10 h-10 rounded-full bg-red-50 border border-red-100 text-red-500 flex items-center justify-center hover:bg-red-500 hover:text-white transition-all">
            <LogOut size={18} />
          </button>
        </div>
      </nav>

      <div className="flex-1 flex flex-col md:flex-row h-[calc(100vh-80px)] overflow-hidden">
        <aside className="w-full md:w-20 border-r border-slate-200 flex flex-col items-center py-8 gap-10 bg-white">
          <button onClick={() => alert('No new high-priority clinical alerts.')} title="Alerts" className="w-12 h-12 rounded-xl bg-slate-50 text-slate-400 flex items-center justify-center hover:bg-blue-50 hover:text-blue-600 transition-all border border-slate-100">
            <Bell size={20} />
          </button>
          <button onClick={() => alert('Opening hospital system configuration...')} title="Settings" className="w-12 h-12 rounded-xl bg-slate-50 text-slate-400 flex items-center justify-center hover:bg-blue-50 hover:text-blue-600 transition-all border border-slate-100">
            <Settings size={20} />
          </button>
          <div className="flex-1"></div>
        </aside>

        <main className="flex-1 p-8 overflow-y-auto bg-slate-50 custom-scrollbar">
          <div className="max-w-6xl mx-auto space-y-10">
            
            <header className="directory-header flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-slate-200/60 pb-8">
              <div>
                <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">Clinical Records Access</h2>
                <p className="text-slate-500 mt-2 font-medium">Search and select validated patient identities for scientific processing.</p>
              </div>
              <div className="flex items-center gap-6 text-center">
                <div className="bg-white border border-slate-200 py-3 px-8 rounded-2xl shadow-sm">
                   <span className="text-blue-600 font-black text-2xl block leading-none mb-1">{patients.length}</span>
                   <span className="text-[8px] text-slate-400 uppercase font-black tracking-widest leading-none">Total Registry</span>
                </div>
              </div>
            </header>

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-7 flex items-center pointer-events-none">
                <Search size={22} className="text-slate-400 group-focus-within:text-blue-600 transition-colors" />
              </div>
              <input 
                type="text"
                placeholder="Lookup patient via Identifier, Full Name, or Phone..."
                className="w-full h-20 bg-white border border-slate-200 rounded-2xl pl-16 pr-8 text-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 transition-all shadow-sm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <div className="absolute right-6 top-1/2 -translate-y-1/2 flex items-center gap-3">
                <button 
                  onClick={() => {
                    gsap.fromTo(".refresh-icon", { rotation: 0 }, { rotation: 360, duration: 1, ease: "power2.out" });
                    fetchDirectory(false);
                  }} 
                  title="Sync Registry"
                  className="w-10 h-10 flex items-center justify-center text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-xl transition-all"
                >
                  <RefreshCcw size={18} className="refresh-icon" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {patients.map(patient => (
                <div 
                  key={patient.patient_uid} 
                  onClick={() => router.push(`/patient/${patient.patient_uid}`)}
                  className="patient-card glass-panel p-8 group transition-all h-full min-h-[400px] bg-white border border-slate-200 hover:border-blue-400 hover:shadow-2xl hover:shadow-blue-600/10 flex flex-col relative overflow-hidden cursor-pointer rounded-3xl"
                >
                  <div className="flex justify-between items-start mb-6 z-10">
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all group-hover:scale-110 bg-blue-50 text-blue-600 border border-blue-100">
                         <Activity size={28} />
                      </div>
                      <div>
                        <h3 className="text-2xl font-extrabold text-slate-900 leading-tight group-hover:text-blue-600 transition-colors">
                          {patient.full_name}
                        </h3>
                        <span className="text-sm font-mono text-slate-500 font-bold">{patient.patient_uid}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1 text-right">
                       <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full ${patient.patient_category === 'geriatric' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'}`}>
                         {patient.patient_category || 'Neurology'}
                       </span>
                    </div>
                  </div>
                  
                  <div className="flex-1 z-10 flex flex-col gap-4 mt-2">
                    
                    {/* Primary Medical Data */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex flex-col items-center text-center">
                        <span className="text-[9px] text-slate-400 uppercase tracking-widest font-black mb-1">Age / DOB</span>
                        <span className="text-slate-900 font-bold text-sm tracking-tight">{patient.date_of_birth}</span>
                      </div>
                      <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex flex-col items-center text-center">
                        <span className="text-[9px] text-slate-400 uppercase tracking-widest font-black mb-1">Gender</span>
                        <span className="text-slate-900 font-bold text-sm tracking-tight">{patient.gender}</span>
                      </div>
                      <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex flex-col items-center text-center">
                         <span className="text-[9px] text-slate-400 uppercase tracking-widest font-black mb-1">Blood</span>
                         <span className="text-slate-900 font-black text-sm text-red-500">{patient.blood_type || 'Unk'}</span>
                      </div>
                    </div>

                    {/* Hospital Admission Details */}
                    <div className="p-4 bg-blue-50/50 border border-blue-100/50 rounded-xl space-y-3">
                      <div className="flex justify-between items-center pb-2 border-b border-blue-100">
                         <div className="flex flex-col">
                           <span className="text-[9px] text-blue-400 uppercase tracking-widest font-black mb-1">Ward Location</span>
                           <span className="text-slate-800 font-bold text-sm tracking-tight flex items-center gap-2">
                              {patient.ward_area || 'Neurology Dept'}
                           </span>
                         </div>
                         <div className="flex flex-col items-end">
                           <span className="text-[9px] text-blue-400 uppercase tracking-widest font-black mb-1">Bed No.</span>
                           <span className="text-slate-800 font-bold text-sm tracking-tight">{patient.bed_no || 'Pending Allocation'}</span>
                         </div>
                      </div>
                      
                      <div className="flex justify-between items-start pt-1">
                         <div className="flex flex-col">
                           <span className="text-[9px] text-blue-400 uppercase tracking-widest font-black mb-1">Primary Diagnosis</span>
                           <span className="text-slate-800 font-bold text-sm tracking-tight">{patient.primary_diagnosis || 'Undiagnosed / Triaging'}</span>
                         </div>
                      </div>
                    </div>
                    
                    {/* Assigned Provider */}
                    <div className="flex items-center gap-3 px-1 mt-auto">
                       <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                         <UserCircle size={18} />
                       </div>
                       <div className="flex flex-col">
                         <span className="text-[9px] text-slate-400 uppercase tracking-widest font-black leading-tight">Attending Physician</span>
                         <span className="text-slate-700 font-bold text-xs">{patient.primary_doctor_id === 1 ? 'Dr. Sarah Chen' : 'Neuro Dept Authority'}</span>
                       </div>
                    </div>

                  </div>

                  <div className="mt-8 pt-5 border-t border-slate-100 z-10 w-full">
                     <button className="w-full h-12 bg-blue-600 text-white rounded-xl flex items-center justify-center gap-3 transition-all font-bold group-hover:bg-blue-700 shadow-lg shadow-blue-600/10 group-hover:shadow-blue-600/30">
                        <span className="tracking-tight">Scientific Dossier Access</span>
                        <ChevronRight size={18} className="translate-x-0 group-hover:translate-x-1 transition-transform" />
                     </button>
                  </div>

                  <div className="absolute bottom-[-20%] right-[-10%] w-64 h-64 bg-blue-50 rounded-full blur-3xl opacity-20 pointer-events-none" />
                </div>
              ))}
              
              {patients.length === 0 && (
                <div className="col-span-full py-40 flex flex-col items-center justify-center bg-white rounded-3xl border-2 border-dashed border-slate-200">
                   <div className="w-24 h-24 rounded-full bg-slate-50 flex items-center justify-center text-slate-200 mb-8">
                     <Search size={48} />
                   </div>
                   <h3 className="text-2xl font-bold text-slate-400">No Matches Found</h3>
                   <p className="text-slate-500 mt-2 font-medium">Verify the clinical identifier or adjust search parameters.</p>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
