export function resolveApiBase(configured: string | undefined, isDevelopment: boolean): string {
  const apiBase = configured?.trim().replace(/\/+$/, "");
  if (apiBase) return apiBase;
  return isDevelopment ? "http://localhost:8000" : "";
}
