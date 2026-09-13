import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { API_MODE } from "../api";
import { supabase } from "../auth/supabase";

// Districts and company names deliberately are NOT listed here. Which real
// enterprise each demo account maps to is decided by the backend seed from the
// UDYAM dataset, so anything written here drifts the moment the seed or the
// dataset changes. The quantities and prices below come from fixed values in
// the seed and are stable. The signed-in business is shown on the dashboard.
const DEMO_PERSONAS = [
  {
    role: "Buyer 1 — brick kiln",
    email: "buyer1@demo.bitnbuild.local",
    desc: "Sourcing 20 t rice husk as kiln fuel",
    icon: "🧱",
  },
  {
    role: "Seller 1 — rice mill",
    email: "seller1@demo.bitnbuild.local",
    desc: "Lists 60 t rice husk @ ₹3,050/t",
    icon: "🌾",
  },
  {
    role: "Seller 2 — rice mill",
    email: "seller2@demo.bitnbuild.local",
    desc: "Lists 45 t rice husk @ ₹2,620/t",
    icon: "🌾",
  },
  {
    role: "Seller 3 — rice mill",
    email: "seller3@demo.bitnbuild.local",
    desc: "Lists 40 t rice husk @ ₹2,750/t",
    icon: "🌾",
  },
  {
    role: "Buyer 2 — sawmill boiler",
    email: "buyer2@demo.bitnbuild.local",
    desc: "Sourcing 15 t rice husk for timber drying",
    icon: "🌲",
  },
];

export function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(targetEmail: string, targetPassword?: string) {
    setError(null);
    setSubmitting(true);
    try {
      if (API_MODE === "real") {
        await signIn(targetEmail, targetPassword || undefined);
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await handleLogin(email, password);
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Sign in</h1>
        <p className="auth-card__hint">
          {API_MODE === "real"
            ? supabase
              ? "Sign in with your registered account."
              : "Choose a demo account below, or enter your email address."
            : "Demo preview with sample data. Any details will sign you in."}
        </p>

        <div className="persona-grid" style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1.25rem" }}>
          <span className="eyebrow" style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>
            Quick Demo Personas
          </span>
          {DEMO_PERSONAS.map((p) => (
            <button
              key={p.email}
              type="button"
              className="button button--ghost"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.6rem 0.8rem",
                textAlign: "left",
                fontSize: "0.85rem",
              }}
              onClick={() => {
                setEmail(p.email);
                handleLogin(p.email);
              }}
              disabled={submitting}
            >
              <div>
                <strong>{p.icon} {p.role}</strong>
                <div style={{ fontSize: "0.75rem", opacity: 0.8 }}>{p.email}</div>
              </div>
              <span style={{ fontSize: "0.8rem", color: "var(--accent)" }}>Select →</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          {supabase && (
            <label>
              Password
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
          )}
          {error && <p className="form-error">{error}</p>}
          <button className="button button--primary" type="submit" disabled={submitting} style={{ width: "100%", marginTop: "0.5rem" }}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
