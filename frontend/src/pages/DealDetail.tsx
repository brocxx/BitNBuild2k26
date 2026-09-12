import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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

      <h3>Cost</h3>
      <CostBreakdown costs={deal.costs} />

      <div className="deal-actions">
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
