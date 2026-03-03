const BASE =
  typeof process !== "undefined"
    ? (process.env.API_URL ?? "http://localhost:3069")
    : (import.meta.env.VITE_API_URL ?? "http://localhost:3069");

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  patients: {
    list: () => apiFetch("/patients"),
    get: (id: string) => apiFetch(`/patients/${id}`),
  },
  readings: {
    list: (patientId: string, limit = 30) =>
      apiFetch(`/readings?patient_id=${patientId}&limit=${limit}`),
    review: (id: string) => apiFetch(`/readings/${id}/review`, { method: "PATCH" }),
  },
};
