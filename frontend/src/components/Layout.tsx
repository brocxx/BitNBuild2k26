import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api";
import type { Business } from "../api";
import { useAuth } from "../auth/AuthContext";

const NAV = [
  { to: "/", label: "Overview", icon: "◫", end: true },
  { to: "/listings", label: "My byproducts", icon: "◌" },
  { to: "/requirements", label: "Requirements", icon: "◎" },
  { to: "/opportunities", label: "Opportunity lab", icon: "✦" },
];

export function Layout() {
  const { isAuthenticated, signOut } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("kib-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("kib-theme", theme);
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    api.getMe()
      .then((me) => { if (!cancelled && me?.business) setBusiness(me.business); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [isAuthenticated]);

  const initials = business?.name
    ? business.name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase()
    : "KB";

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
            <NavLink key={item.to} to={item.to} end={item.end}
              className={({ isActive }) => `side-link${isActive ? " side-link--active" : ""}`}>
              <span className="side-link__icon">{item.icon}</span><span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-spacer" />
        <button className="theme-toggle" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
          <span>{theme === "light" ? "☾" : "☀"}</span>
          <span>{theme === "light" ? "Dark mode" : "Light mode"}</span>
        </button>
        <div className="enterprise-chip">
          <div className="avatar">{initials}</div>
          <div style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
            <strong>{business?.name || "Your enterprise"}</strong>
            <span>{business ? `${business.location.district} · ${business.enterprise_id || business.roles.join(" / ")}` : "Karnataka"}</span>
          </div>
        </div>
        {isAuthenticated && <button className="button button--ghost button--full" onClick={() => signOut()}>Sign out</button>}
      </aside>

      <main className="workspace">
        <div className="page-wrap"><Outlet /></div>
      </main>
    </div>
  );
}
