import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { API_MODE } from "../api";
import { supabase } from "../auth/supabase";

const DEMO_PERSONAS = [
  {
    role: "Buyer 1 (Brick Kiln - Kolar)",
    email: "buyer1@demo.bitnbuild.local",
    desc: "Has active Rice Husk requirement with budget",
    icon: "🧱",
  },
  {
    role: "Seller 1 (Rice Mill - Nearest)",
    email: "seller1@demo.bitnbuild.local",
    desc: "Lists 60 tonnes Rice Husk @ ₹3,050/t (Kolar)",
    icon: "🌾",
  },
  {
    role: "Seller 2 (Rice Mill - Mid-range)",
    email: "seller2@demo.bitnbuild.local",
    desc: "Lists 45 tonnes Rice Husk @ ₹2,620/t",
    icon: "🌾",
  },
  {
    role: "Buyer 2 (Sawmill Boiler)",
    email: "buyer2@demo.bitnbuild.local",
    desc: "Timber drying boiler secondary fuel buyer",
    icon: "🌲",
  },
];

export function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("buyer1@demo.bitnbuild.local");
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
              ? "Connected to Supabase. Sign in with your registered account."
              : "Connected to Local FastAPI Backend. Select a seeded demo account below or enter an address."
            : "Mock Mode — Any credentials will sign you in with mock fixtures."}
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
