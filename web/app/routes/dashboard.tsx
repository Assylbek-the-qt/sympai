import { useLoaderData, Link } from "react-router";
import { api } from "../lib/api";

export async function loader() {
  const patients = await api.patients.list();
  return { patients };
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

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-6 py-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-semibold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { patients } = useLoaderData<typeof loader>();

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
      </header>

      <main className="px-8 py-8 max-w-7xl mx-auto">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Patients" value={total} />
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
