import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/dashboard.tsx"),
  route("patients/:id", "routes/patients.$id.tsx"),
] satisfies RouteConfig;
