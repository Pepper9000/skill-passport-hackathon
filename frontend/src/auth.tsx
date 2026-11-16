import React, { createContext, useContext, useEffect, useState } from "react";
import { api, setAuthRequiredHandler } from "./api";
import {
  type User,
  type UserRole,
  canAccessRoute,
  displayNameFromLogin,
  parseStoredUser,
  PRESET_LOGINS,
} from "./authTypes";

export type { User, UserRole };
export { canAccessRoute };

const STORAGE_KEY = "skill_passport_auth_session";
const LOGIN_DISMISSED_KEY = "skill_passport_login_dismissed";
const SESSION_ENDED = "Your recruiter session has ended. Sign in again to continue.";

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoginModalOpen: boolean;
  /** Why the last recruiter sign-in or session failed (shown in the sign-in modal). */
  authError: string;
  openLoginModal: () => void;
  closeLoginModal: () => void;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  quickLogin: (role: UserRole) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * The recruiter role comes only from the server: the password is exchanged at
 * /auth/recruiter/login for a session token, which every recruiter endpoint checks.
 * Returns an error message, or null on success.
 */
async function recruiterSignIn(
  password: string,
  username: string,
): Promise<{ recruiter_id: string; read_only: boolean } | { error: string }> {
  try {
    return await api.recruiterLogin(password, username);
  } catch (reason) {
    // A development server with no recruiter key configured leaves recruiter routes open.
    const open = await api.me().catch(() => null);
    if (open && !open.auth_required) return { recruiter_id: open.recruiter_id, read_only: open.read_only };
    return { error: reason instanceof Error ? reason.message : "Recruiter sign-in failed." };
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [initialSession] = useState(() => {
    try {
      // A restored recruiter profile is not trusted on its own: the effect below confirms it
      // with /auth/me. A keyless development server holds no token, yet its sign-in is valid,
      // so the profile is kept until the server answers instead of being dropped on refresh.
      const user = parseStoredUser(localStorage.getItem(STORAGE_KEY));
      return { user, isLoginModalOpen: false };
    } catch {
      return { user: null, isLoginModalOpen: false };
    }
  });
  const [user, setUser] = useState<User | null>(initialSession.user?.role === "student" ? initialSession.user : null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(initialSession.isLoginModalOpen);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    const endRecruiterSession = () => {
      setUser((current) => (current?.role === "recruiter" ? null : current));
      setAuthError(SESSION_ENDED);
      setIsLoginModalOpen(true);
    };
    setAuthRequiredHandler(endRecruiterSession);
    // Re-check a restored recruiter profile with the server: the token may have expired or been
    // revoked, or there may be no token at all (a keyless development server confirms via /auth/me).
    if (initialSession.user?.role === "recruiter") {
      api.me().then((identity) => {
        if (!identity) {
          endRecruiterSession();
        } else {
          setUser((current) => current?.role === "recruiter"
            ? { ...current, id: identity.recruiter_id, readOnly: identity.read_only }
            : initialSession.user ? { ...initialSession.user, id: identity.recruiter_id, name: displayNameFromLogin(identity.recruiter_id), readOnly: identity.read_only } : null);
        }
      }).catch(() => undefined);
    }
    return () => setAuthRequiredHandler(null);
  }, [initialSession]);

  useEffect(() => {
    try {
      if (user) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // storage unavailable
    }
  }, [user]);

  const setRecruiter = (recruiter: User) => {
    setAuthError("");
    setUser(recruiter);
    setIsLoginModalOpen(false);
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    const trimmedEmail = email.trim();
    const trimmedPass = password;

    if (!trimmedEmail) {
      return { success: false, error: "Please enter an email or username." };
    }
    if (!trimmedPass) {
      return { success: false, error: "Please enter a password." };
    }

    if (trimmedEmail.toLowerCase() === PRESET_LOGINS.student.username) {
      if (password !== PRESET_LOGINS.student.password) return { success: false, error: "That student password is not valid." };
      await api.recruiterLogout();
      setAuthError("");
      setUser({ id: "student", name: "Student", email: PRESET_LOGINS.student.username, role: "student", title: "Student", organization: "" });
      setIsLoginModalOpen(false);
      return { success: true };
    }
    const result = await recruiterSignIn(password, trimmedEmail);
    if ("error" in result) return { success: false, error: result.error };
    setRecruiter({
      id: result.recruiter_id,
      name: displayNameFromLogin(result.recruiter_id),
      email: trimmedEmail,
      role: "recruiter",
      title: "Recruiter",
      organization: "",
      readOnly: result.read_only,
    });
    return { success: true };
  };

  const switchRole = async (_newRole: UserRole) => {
    setAuthError("");
    setIsLoginModalOpen(true);
  };

  const quickLogin = switchRole;

  const logout = () => {
    void api.recruiterLogout();
    setAuthError("");
    setUser(null);
    setIsLoginModalOpen(true);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role ?? null,
        isAuthenticated: !!user,
        isLoginModalOpen,
        authError,
        openLoginModal: () => setIsLoginModalOpen(true),
        closeLoginModal: () => {
          try {
            sessionStorage.setItem(LOGIN_DISMISSED_KEY, "1");
          } catch {
            // storage unavailable
          }
          setIsLoginModalOpen(false);
        },
        login,
        quickLogin,
        logout,
        switchRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
  }
