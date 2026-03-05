import { useLoaderData, Link, redirect, useNavigate } from "react-router";
import { useEffect } from "react";
import { api } from "../lib/api";
import type { Route } from "./+types/dashboard";

export async function loader({ request }: Route.LoaderArgs) {
  const url = new URL(request.url);
  const tokenFromUrl = url.searchParams.get("token");
  if (tokenFromUrl) {
    return { patients: [], stats: null, pendingToken: tokenFromUrl };
  }
  const [patients, stats] = await Promise.all([
    api.patients.list(),
    api.patients.stats(),
  ]);
  return { patients, stats, pendingToken: null };
}

export function meta() {
  return [{ title: "SympAI — Dashboard" }];
}

const DIAGNOSIS_LABEL: Record<string, string> = {
  hypertension: "Hypertension",
  diabetes: "Diabetes",
  both: "Both",
};

const DIAGNOSIS_COLOR: Record<string, string> = {
  hypertension: "bg-blue-100 text-blue-800",
  diabetes:     "bg-purple-100 text-purple-800",
  both:         "bg-orange-100 text-orange-800",
};

function StatCard({ label, value, sub, accent }: { label: string; value: number | string; sub?: string; accent?: "red" | "yellow" | "green" }) {
  const border = accent === "red" ? "border-red-200 bg-red-50" : accent === "yellow" ? "border-yellow-200 bg-yellow-50" : "bg-white border-gray-200";
  const text = accent === "red" ? "text-red-700" : accent === "yellow" ? "text-yellow-700" : "text-gray-900";
  return (
    <div className={`rounded-xl border px-6 py-5 ${border}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-semibold mt-1 ${text}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { patients, stats, pendingToken } = useLoaderData<typeof loader>();
  const navigate = useNavigate();

  useEffect(() => {
    if (pendingToken) {
      localStorage.setItem("token", pendingToken);
      navigate("/", { replace: true });
      return;
    }
    if (!localStorage.getItem("token")) {
      navigate("/login", { replace: true });
    }
  }, [pendingToken]);

  const total = patients.length;
  const hypertension = patients.filter((p: any) => p.diagnosis === "hypertension").length;
  const diabetes = patients.filter((p: any) => p.diagnosis === "diabetes").length;
  const both = patients.filter((p: any) => p.diagnosis === "both").length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">SympAI</h1>
          <p className="text-xs text-gray-400">Hypertension Monitoring</p>
        </div>
        <button
          onClick={() => { localStorage.removeItem("token"); navigate("/login", { replace: true }); }}
          className="text-xs text-gray-400 hover:text-gray-700"
        >
          Sign out
        </button>
      </header>

      <main className="px-8 py-8 max-w-7xl mx-auto">
        {/* Key metrics row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <StatCard label="Total Patients" value={stats?.total_patients ?? total} />
          <StatCard
            label="High Risk"
            value={stats?.high_risk_count ?? "—"}
            sub="latest reading"
            accent={stats?.high_risk_count > 0 ? "red" : undefined}
          />
          <StatCard
            label="Avg Compliance"
            value={stats ? `${stats.avg_compliance_pct}%` : "—"}
            sub="last 30 days"
            accent={stats?.avg_compliance_pct < 60 ? "yellow" : "green"}
          />
          <StatCard
            label="Missed Today"
            value={stats ? `${stats.missed_today_pct}%` : "—"}
            sub={stats ? `${stats.missed_today} patients` : undefined}
            accent={stats?.missed_today_pct > 30 ? "yellow" : undefined}
          />
        </div>

        {/* Diagnosis breakdown row */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <StatCard label="Hypertension" value={hypertension} sub={`${Math.round((hypertension / total) * 100) || 0}% of patients`} />
          <StatCard label="Diabetes" value={diabetes} sub={`${Math.round((diabetes / total) * 100) || 0}% of patients`} />
          <StatCard label="Both" value={both} sub={`${Math.round((both / total) * 100) || 0}% of patients`} />
        </div>

        {/* Patient table */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">All Patients</h2>
            <span className="text-xs text-gray-400">{total} total</span>
          </div>

          {patients.length === 0 ? (
            <div className="px-6 py-16 text-center text-gray-400 text-sm">No patients yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-6 py-3 text-left font-medium">Name</th>
                    <th className="px-6 py-3 text-left font-medium">Age</th>
                    <th className="px-6 py-3 text-left font-medium">Diagnosis</th>
                    <th className="px-6 py-3 text-left font-medium">Medication</th>
                    <th className="px-6 py-3 text-left font-medium">Language</th>
                    <th className="px-6 py-3 text-left font-medium">Registered</th>
                    <th className="px-6 py-3 text-left font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {patients.map((p: any) => (
                    <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-900">{p.full_name}</td>
                      <td className="px-6 py-4 text-gray-600">{p.age}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${DIAGNOSIS_COLOR[p.diagnosis] ?? "bg-gray-100 text-gray-700"}`}>
                          {DIAGNOSIS_LABEL[p.diagnosis] ?? p.diagnosis}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-600">{p.current_medication ?? "—"}</td>
                      <td className="px-6 py-4 text-gray-500 uppercase text-xs">{p.language}</td>
                      <td className="px-6 py-4 text-gray-400 text-xs">
                        {new Date(p.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <Link
                          to={`/patients/${p.id}`}
                          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                        >
                          View →
                        </Link>
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
