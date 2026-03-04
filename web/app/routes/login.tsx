import { Form, redirect, useActionData, useNavigation } from "react-router";
import type { Route } from "./+types/login";

const BASE =
  typeof process !== "undefined"
    ? (process.env.API_URL ?? "http://localhost:3069")
    : (import.meta.env.VITE_API_URL ?? "http://localhost:3069");

export async function action({ request }: Route.ActionArgs) {
  const form = await request.formData();
  const email = form.get("email") as string;
  const password = form.get("password") as string;

  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    return { error: "Invalid email or password" };
  }

  const { access_token } = await res.json();
  // Token is stored client-side after redirect — see below
  return redirect(`/?token=${access_token}`);
}

export function meta() {
  return [{ title: "SympAI — Login" }];
}

export default function Login() {
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const isLoading = navigation.state === "submitting";

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl border border-gray-200 px-8 py-10 w-full max-w-sm">
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-gray-900">SympAI</h1>
          <p className="text-sm text-gray-400 mt-1">Doctor dashboard</p>
        </div>

        <Form method="post" className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {actionData?.error && (
            <p className="text-sm text-red-600">{actionData.error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="mt-2 w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg text-sm transition-colors"
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </Form>
      </div>
    </div>
  );
}
