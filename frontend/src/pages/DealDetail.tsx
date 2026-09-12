import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { Deal, DealStatus } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { CostBreakdown } from "../components/CostBreakdown";
import { kgToTonnes, formatDateTime, metersToKm } from "../utils/format";

const NEXT_STATUS: Partial<Record<DealStatus, DealStatus>> = {
  agreed: "pickup_scheduled",
  pickup_scheduled: "collected",
  collected: "delivered",
};

export function DealDetail() {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const [deal, setDeal] = useState<Deal | null>(null);
  const [updating, setUpdating] = useState(false);

  async function refresh() {
    if (!dealId) return;
    const res = await api.getDeal(dealId);
    setDeal(res);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dealId]);

  async function advance() {
    if (!deal) return;
    const next = NEXT_STATUS[deal.status];
    if (!next) return;
    setUpdating(true);
    try {
      await api.updateDealStatus(deal.id, next);
      await refresh();
    } finally {
      setUpdating(false);
    }
  }

  async function cancel() {
    if (!deal) return;
    setUpdating(true);
    try {
      await api.updateDealStatus(deal.id, "cancelled");
      await refresh();
    } finally {
      setUpdating(false);
    }
  }

  function downloadSummary() {
    if (!deal) return;
    const blob = new Blob([JSON.stringify(deal, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deal-${deal.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!deal) return <p className="loading">Loading deal…</p>;

  const next = NEXT_STATUS[deal.status];
  const canCancel = deal.status === "agreed" || deal.status === "pickup_scheduled";
  const esg = deal.esg_metrics;

  return (
    <div className="panel">
      <div className="panel__header">
        <h2>Deal {deal.id}</h2>
        <StatusBadge status={deal.status} />
      </div>

      <div className="deal-grid">
        <div>
          <h3>Parties</h3>
          <p>Seller: {deal.seller.name} ({deal.seller.location.district})</p>
          <p>Buyer: {deal.buyer.name} ({deal.buyer.location.district})</p>
        </div>
        <div>
          <h3>Material</h3>
          <p>{deal.material_id.replace("_", " ")} · {kgToTonnes(deal.quantity_kg)} t</p>
          <p className="muted">Intended use: {deal.intended_use.replace(/_/g, " ")}</p>
        </div>
        <div>
          <h3>Route</h3>
          <p>{deal.transport_option.label}</p>
          <p className="muted">
            {metersToKm(deal.transport_option.distance_m)} ({deal.transport_option.distance_basis.replace(/_/g, " ")}) —
            {" "}{deal.transport_option.source === "configured_estimate" ? "configured estimate" : "entered quote"}
          </p>
          <p className="muted">
            Pickup {formatDateTime(deal.transport_option.pickup_at)} → Delivery {formatDateTime(deal.transport_option.delivery_at)}
          </p>
        </div>
      </div>

      {esg && (
        <div style={{ background: "#e8f8f0", border: "1px solid #a3e4d7", borderRadius: "8px", padding: "1.2rem", margin: "1.5rem 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
            <h3 style={{ margin: 0, color: "#16a085", fontSize: "1.05rem" }}>🌿 Verified ESG Impact</h3>
            <span style={{ fontSize: "0.8rem", background: "#27ae60", color: "#fff", padding: "0.15rem 0.5rem", borderRadius: "4px" }}>
              IPCC 2006 Standard
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginTop: "0.75rem" }}>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Net CO₂e Saved</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#27ae60" }}>
                {(esg.net_co2e_avoided_kg / 1000).toFixed(2)} tonnes
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Landfill Diverted</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#2980b9" }}>
                {(esg.landfill_diverted_kg / 1000).toFixed(2)} tonnes
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Carbon Credits</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#b7950b" }}>
                {esg.carbon_credits_estimated.toFixed(3)} tCO₂e
              </div>
            </div>
          </div>
        </div>
      )}

      <h3>Cost</h3>
      <CostBreakdown costs={deal.costs} />

      <div className="deal-actions" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "1.5rem" }}>
        <button
          className="button button--primary"
          style={{ background: "#27ae60", borderColor: "#27ae60" }}
          onClick={() => navigate(`/deals/${deal.id}/certificate`)}
        >
          🌿 View Digital Green Certificate →
        </button>
        {next && (
          <button className="button button--primary" onClick={advance} disabled={updating}>
            Mark {next.replace(/_/g, " ")}
          </button>
        )}
        {canCancel && (
          <button className="button button--ghost" onClick={cancel} disabled={updating}>
            Cancel deal
          </button>
        )}
        <button className="button button--ghost" onClick={downloadSummary}>
          Download summary (JSON)
        </button>
      </div>
    </div>
  );
}

