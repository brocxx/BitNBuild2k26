import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Listings } from "./pages/Listings";
import { Requirements } from "./pages/Requirements";
import { Matches } from "./pages/Matches";
import { NegotiationDetail } from "./pages/NegotiationDetail";
import { DealDetail } from "./pages/DealDetail";
import { OpportunityLab } from "./pages/OpportunityLab";
import { useAuth } from "./auth/AuthContext";
import { API_MODE } from "./api";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { loading, session } = useAuth();
  if (API_MODE !== "real") return children; // mock mode skips real auth entirely
  if (loading) return <p className="loading">Loading…</p>;
  if (!session) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/listings" element={<Listings />} />
        <Route path="/requirements" element={<Requirements />} />
        <Route path="/opportunities" element={<OpportunityLab />} />
        <Route path="/requirements/:requirementId/matches" element={<Matches />} />
        <Route path="/negotiations/:negotiationId" element={<NegotiationDetail />} />
        <Route path="/deals/:dealId" element={<DealDetail />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
