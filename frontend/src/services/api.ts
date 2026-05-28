// frontend/src/services/api.ts
// Using relative paths to leverage Next.js rewrites in next.config.ts
const API_BASE = "/api/v1";

function getAuthHeaders(extraHeaders = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('hospital_token') : null;
  return {
    ...extraHeaders,
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
}

export async function fetchPatients() {
  const res = await fetch(`${API_BASE}/patients/search`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error("Failed to fetch patients");
  return res.json();
}

export async function fetchPatientAnalysis(uid: string) {
  const res = await fetch(`${API_BASE}/patients/${uid}/summary`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error("Failed to fetch analysis");
  return res.json();
}

export async function submitTriage(data: any) {
  const res = await fetch(`${API_BASE}/triage/assess`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error("Triage submission failed");
  return res.json();
}

export async function triggerFullPipeline(uid: string) {
  const res = await fetch(`${API_BASE}/patients/${uid}/full-pipeline`, {
    method: "POST",
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error("Pipeline trigger failed");
  return res.json();
}

// ── Recovery Intelligence Engine ─────────────────────────────────────────────

export async function fetchRecoveryAnalysis(uid: string) {
  const res = await fetch(`${API_BASE}/patients/${uid}/recovery/analysis`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error("Recovery analysis failed");
  return res.json();
}

export async function fetchRecoveryTrajectory(uid: string) {
  const res = await fetch(`${API_BASE}/patients/${uid}/recovery/trajectory`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error("Recovery trajectory failed");
  return res.json();
}

export async function fetchRecoveryMedications(uid: string) {
  const res = await fetch(`${API_BASE}/patients/${uid}/recovery/medications`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error("Medication protocol failed");
  return res.json();
}

export async function simulateRecoveryIntervention(uid: string, interventions: Record<string, number>, infarct_volume_ml?: number) {
  const body: any = { interventions };
  if (infarct_volume_ml !== undefined) body.infarct_volume_ml = infarct_volume_ml;
  
  const res = await fetch(`${API_BASE}/patients/${uid}/recovery/simulate`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error("Recovery simulation failed");
  return res.json();
}
