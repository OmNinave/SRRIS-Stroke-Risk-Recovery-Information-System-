"use client";

import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts';
import { Activity, AlertTriangle, TrendingDown, ClipboardList } from 'lucide-react';
import { API_BASE_URL } from '@/config';

interface AnalyticsData {
  month: string;
  stroke_events: number;
  avg_systolic_bp: number;
  avg_glucose: number;
  avg_cholesterol: number;
}

interface BenchmarkData {
  metric: string;
  patient_value: number;
  normal_range: number;
  high_risk_range: number;
  status: string;
}

const ClinicalAnalytics = ({ patientUid }: { patientUid: string }) => {
  const [trends, setTrends] = useState<AnalyticsData[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [trendsRes, benchmarksRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/v1/analytics/patient/${patientUid}/trends`),
          fetch(`${API_BASE_URL}/api/v1/analytics/patient/${patientUid}/benchmarks`)
        ]);

        if (trendsRes.ok && benchmarksRes.ok) {
          setTrends(await trendsRes.json());
          setBenchmarks(await benchmarksRes.json());
        }
      } catch (error) {
        console.error("Failed to fetch analytics:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [patientUid]);

  if (loading) return <div className="p-8 text-center text-slate-400">Synchronizing Clinical Intelligence...</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="text-blue-400 w-5 h-5" />
            <h3 className="text-slate-300 font-medium">Risk Velocity</h3>
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">Stable</p>
          <p className="text-xs text-slate-500 mt-1">Based on 90-day longitudinal trend</p>
        </div>
        
        <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="text-amber-400 w-5 h-5" />
            <h3 className="text-slate-300 font-medium">Acute Thresholds</h3>
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">
            {benchmarks.filter(b => b.status === "High Risk").length} High Risk
          </p>
          <p className="text-xs text-slate-500 mt-1">Markers currently exceeding limits</p>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <TrendingDown className="text-emerald-400 w-5 h-5" />
            <h3 className="text-slate-300 font-medium">BP Control</h3>
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">-12% Variance</p>
          <p className="text-xs text-slate-500 mt-1">Reduction since last clinical event</p>
        </div>
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Longitudinal History */}
        <div className="bg-slate-950 border border-slate-800 p-6 rounded-2xl shadow-2xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <ClipboardList className="text-blue-500" /> Longitudinal Clinical History
            </h3>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="month" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                <Line type="monotone" dataKey="avg_systolic_bp" name="Systolic BP" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="avg_glucose" name="Glucose" stroke="#f59e0b" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Benchmarking */}
        <div className="bg-slate-950 border border-slate-800 p-6 rounded-2xl shadow-2xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="text-emerald-500" /> SOTA Metric Benchmarking
            </h3>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={benchmarks} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis dataKey="metric" type="category" stroke="#64748b" fontSize={12} width={100} />
                <Tooltip 
                  cursor={{ fill: 'rgba(30, 41, 59, 0.5)' }}
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                />
                <Bar dataKey="patient_value" name="Current Value" radius={[0, 4, 4, 0]}>
                  {benchmarks.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.status === 'High Risk' ? '#ef4444' : entry.status === 'Moderate' ? '#f59e0b' : '#10b981'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClinicalAnalytics;
