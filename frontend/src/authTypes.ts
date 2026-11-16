export type UserRole = "student" | "recruiter";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  title: string;
  organization: string;
  readOnly?: boolean;
}

export function canAccessRoute(pathname: string, role: UserRole | null): boolean {
  const path = pathname.toLowerCase();
  if (path === "/" || path.startsWith("/passport") || path === "/student") {
    return true;
  }
  if (path.startsWith("/recruiter") || path.startsWith("/placement")) {
    return role === "recruiter";
  }
  return true;
}

export function displayNameFromLogin(login: string): string {
  return login.split("@")[0].replace(/[._-]/g, " ").trim() || "Student";
}

export function parseStoredUser(value: string | null): User | null {
  if (!value) return null;
  try {
    const user: unknown = JSON.parse(value);
    if (!user || typeof user !== "object") return null;
    const saved = user as Partial<User>;
    return typeof saved.id === "string" && !!saved.id.trim() &&
      typeof saved.name === "string" && !!saved.name.trim() &&
      typeof saved.email === "string" && !!saved.email.trim() &&
      saved.role === "recruiter" &&
      typeof saved.title === "string" &&
      typeof saved.organization === "string" &&
      (saved.readOnly === undefined || typeof saved.readOnly === "boolean")
      ? saved as User
      : null;
  } catch {
    return null;
  }
}
