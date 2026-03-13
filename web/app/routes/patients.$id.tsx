import { useLoaderData, Link, useNavigate } from "react-router";
import { useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api } from "../lib/api";

export async function loader({ params }: { params: { id: string } }) {
  const [patient, readings, compliance] = await Promise.all([
    api.patients.get(params.id),
    api.readings.list(params.id, 30),
    api.patients.compliance(params.id),
  ]);
  return { patient, readings, compliance };
}

export function meta({ data }: any) {
  return [{ title: `SympAI — ${data?.patient?.full_name ?? "Patient"}` }];
}

const RISK_COLOR: Record<string, string> = {
  low:      "bg-green-100 text-green-800",
  medium:   "bg-yellow-100 text-yellow-800",
  high:     "bg-red-100 text-red-800",
  critical: "bg-purple-100 text-purple-800",
};

export default function PatientDetail() {
  const { patient, readings, compliance } = useLoaderData<typeof loader>();
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      navigate("/login", { replace: true });
    }
  }, []);

  // Recharts needs oldest → newest
  const chartData = [...readings]
    .reverse()
    .map((r: any) => ({ date: r.reading_date, SBP: r.sbp, DBP: r.dbp }));

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-8 py-4 flex items-center gap-4">
        <Link to="/" className="text-sm text-gray-500 hover:text-gray-700">← Dashboard</Link>
        <div>
          <h1 className="text-xl font-semibold text-gray-900">{patient.full_name}</h1>
          <p className="text-xs text-gray-400">Age {patient.age} · {patient.diagnosis} · {patient.language.toUpperCase()}</p>
        </div>
      </header>

      <main className="px-8 py-8 max-w-5xl mx-auto space-y-6">
        {/* Patient info + compliance */}
        <div className="bg-white rounded-xl border border-gray-200 px-6 py-5 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div><p className="text-gray-400 text-xs">Medication</p><p className="text-gray-800 mt-0.5">{patient.current_medication ?? "—"}</p></div>
          <div><p className="text-gray-400 text-xs">Telegram ID</p><p className="text-gray-800 mt-0.5">{patient.telegram_id}</p></div>
          <div><p className="text-gray-400 text-xs">Registered</p><p className="text-gray-800 mt-0.5">{new Date(patient.created_at).toLocaleDateString()}</p></div>
          <div>
            <p className="text-gray-400 text-xs">Compliance (30d)</p>
            <p className={`text-lg font-semibold mt-0.5 ${compliance.compliance_pct >= 70 ? "text-green-600" : compliance.compliance_pct >= 40 ? "text-yellow-600" : "text-red-600"}`}>
              {compliance.compliance_pct}%
            </p>
            <p className="text-xs text-gray-400">{compliance.readings_in_period}/{compliance.total_days} days</p>
          </div>
        </div>

        {/* BP Trend Chart */}
        {chartData.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 px-6 py-5">
            <h2 className="text-sm font-medium text-gray-700 mb-4">Blood Pressure Trend</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis domain={[50, 200]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip />
                <Legend iconType="circle" iconSize={8} />
                <Line type="monotone" dataKey="SBP" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="DBP" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Readings */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">Daily Readings</h2>
            <span className="text-xs text-gray-400">{readings.length} entries</span>
          </div>

          {readings.length === 0 ? (
            <p className="px-6 py-12 text-center text-sm text-gray-400">No readings yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-6 py-3 text-left font-medium">Date</th>
                    <th className="px-6 py-3 text-left font-medium">BP</th>
                    <th className="px-6 py-3 text-left font-medium">Pulse</th>
                    <th className="px-6 py-3 text-left font-medium">Med taken</th>
                    <th className="px-6 py-3 text-left font-medium">Skip reason</th>
                    <th className="px-6 py-3 text-left font-medium">Symptoms</th>
                    <th className="px-6 py-3 text-left font-medium">Risk</th>
                    <th className="px-6 py-3 text-left font-medium">Reviewed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {readings.map((r: any) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 text-gray-600">{r.reading_date}</td>
                      <td className="px-6 py-3 font-medium text-gray-900">{r.sbp}/{r.dbp}</td>
                      <td className="px-6 py-3 text-gray-600">{r.pulse ?? "—"}</td>
                      <td className="px-6 py-3">
                        <span className={r.medication_taken ? "text-green-600" : "text-red-500"}>
                          {r.medication_taken ? "Yes" : "No"}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-gray-500 text-xs">
                        {!r.medication_taken && r.medication_skip_reason ? r.medication_skip_reason : "—"}
                      </td>
                      <td className="px-6 py-3 text-gray-500 text-xs">{r.symptoms?.join(", ") || "—"}</td>
                      <td className="px-6 py-3">
                        {r.risk_level && (
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${RISK_COLOR[r.risk_level]}`}>
                            {r.risk_level}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3 text-gray-400 text-xs">
                        {r.doctor_reviewed_at ? new Date(r.doctor_reviewed_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
