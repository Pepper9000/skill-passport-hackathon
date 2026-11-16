import React, { useEffect, useRef, useState } from "react";
import { ArrowRight, Eye, EyeOff, Lock, Mail, ShieldCheck, X } from "lucide-react";
import { useAuth } from "../auth";
import { PRESET_LOGINS } from "../authTypes";

export default function LoginModal() {
  const { user, isLoginModalOpen, closeLoginModal, login, authError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const emailInputRef = useRef<HTMLInputElement>(null);
  const submitButtonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isLoginModalOpen) return;
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    emailInputRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const trapFocus = (event: KeyboardEvent) => {
      if (event.key === "Escape") { closeLoginModal(); return; }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )];
      if (!focusable.length) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialogRef.current.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialogRef.current.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trapFocus);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", trapFocus);
      previousFocusRef.current?.focus();
    };
  }, [isLoginModalOpen]);

  // When modal opens, initialize empty or with current user's email
  useEffect(() => {
    if (isLoginModalOpen) {
      if (user) {
        setEmail(user.email);
        setPassword("");
      } else {
        setEmail("");
        setPassword("");
      }
      setErrorMessage(authError);
    }
  }, [isLoginModalOpen, user, authError]);

  if (!isLoginModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setSubmitting(true);
    try {
      const res = await login(email, password);
      if (!res.success) {
        setErrorMessage(res.error || "Authentication failed. Please verify your credentials.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <div className="auth-modal-card" ref={dialogRef} tabIndex={-1}>
        <button
          type="button"
          className="auth-modal-close"
          onClick={closeLoginModal}
          aria-label="Close login modal"
        >
          <X size={18} />
        </button>

        <div className="auth-modal-header">
          <div className="auth-modal-brand-badge">
            <ShieldCheck size={28} />
          </div>
          <h2 id="auth-modal-title">Sign in</h2>
          <p className="auth-modal-subtitle">
            Choose a student or recruiter sign-in below, or use your administrator-provided account. Students can also create a passport without signing in.
          </p>
        </div>

        {errorMessage && (
          <div className="notice notice-error auth-modal-alert" role="alert">
            {errorMessage}
          </div>
        )}

        <section className="preset-logins" aria-label="Sign-in options">
          {(["student", "recruiter"] as const).map((role) => <div className="preset-login" key={role}>
            <strong>{role === "student" ? "Student" : "Recruiter"}</strong>
            <span>{PRESET_LOGINS[role].username}</span><code>{PRESET_LOGINS[role].password}</code>
            <button type="button" className="button button-light" onClick={() => {
              setEmail(PRESET_LOGINS[role].username); setPassword(PRESET_LOGINS[role].password); setErrorMessage("");
              submitButtonRef.current?.focus();
            }}>Use {role} sign-in</button>
          </div>)}
        </section>
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="auth-email">Account name</label>
            <div className="auth-input-wrapper">
              <Mail className="auth-input-icon" size={17} />
              <input
                id="auth-email"
                ref={emailInputRef}
                type="text"
                placeholder="Your recruiter account name"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setErrorMessage("");
                }}
                autoComplete="username"
                required
              />
            </div>
          </div>

          <div className="auth-field">
            <div className="auth-field-header">
              <label htmlFor="auth-password">Password</label>
            </div>
            <div className="auth-input-wrapper">
              <Lock className="auth-input-icon" size={17} />
              <input
                id="auth-password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setErrorMessage("");
                }}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            ref={submitButtonRef}
            type="submit"
            className="button auth-submit-button"
            id="auth-submit-btn"
            disabled={submitting}
          >
            <span>{submitting ? "Signing in…" : "Sign in"}</span>
            <ArrowRight size={16} />
          </button>
        </form>

        <p className="muted">Creating a passport? <button type="button" className="link-button" onClick={closeLoginModal}>Continue as a student</button></p>
      </div>
    </div>
  );
}
