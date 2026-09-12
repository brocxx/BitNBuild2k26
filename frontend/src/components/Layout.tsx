import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { API_MODE } from "../api";
import { useAuth } from "../auth/AuthContext";

const NAV = [
  { to: "/", label: "Overview", icon: "◫", end: true },
  { to: "/listings", label: "My byproducts", icon: "◌" },
  { to: "/requirements", label: "Requirements", icon: "◎" },
  { to: "/opportunities", label: "Opportunity lab", icon: "✦" },
];

export function Layout() {
  const { session, signOut } = useAuth();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("kib-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("kib-theme", theme);
  }, [theme]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-kicker">Karnataka</div>
          <div className="brand-script">Circular</div>
          <div className="brand-title">KIB Exchange</div>
          <div className="brand-subtitle">Industrial byproduct network</div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `side-link${isActive ? " side-link--active" : ""}`}
            >
              <span className="side-link__icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-spacer" />
        {API_MODE !== "real" && <div className="demo-pill">● DEMO DATA</div>}
        <button className="theme-toggle" onClick={() => setTheme(theme === "light" ? "dark" : "light")}> 
          <span>{theme === "light" ? "☾" : "☀"}</span>
          <span>{theme === "light" ? "Dark mode" : "Light mode"}</span>
        </button>
        <div className="enterprise-chip">
          <div className="avatar">KB</div>
          <div><strong>KA-ENT-000179</strong><span>Kolar · Brick manufacturing</span></div>
        </div>
        {session && <button className="button button--ghost button--full" onClick={() => signOut()}>Sign out</button>}
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Circular Supply Network · Karnataka</span>
          </div>
          <div className="topbar-actions">
            <span className="evidence-tag">Dataset-backed</span>
            <span className="agent-status"><i /> 3 agents ready</span>
          </div>
        </header>
        <div className="page-wrap"><Outlet /></div>
      </main>
    </div>
  );
}
