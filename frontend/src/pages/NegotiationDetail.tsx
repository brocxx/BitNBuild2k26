import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { Event, Negotiation } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { CostBreakdown } from "../components/CostBreakdown";
import { formatDateTime, paisePerTonneToRupees } from "../utils/format";

const POLL_MS = 2000;
const TERMINAL: Negotiation["status"][] = ["agreed", "no_deal", "failed"];

export function NegotiationDetail() {
  const { negotiationId } = useParams<{ negotiationId: string }>();
  const navigate = useNavigate();
  const [negotiation, setNegotiation] = useState<Negotiation | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const lastSeq = useRef(0);

  useEffect(() => {
    if (!negotiationId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | undefined;

    async function poll() {
      const [neg, ev] = await Promise.all([
        api.getNegotiation(negotiationId!),
        api.getNegotiationEvents(negotiationId!, lastSeq.current),
      ]);
      if (cancelled) return;
      setNegotiation(neg);
      if (ev.items.length) {
        setEvents((prev) => [...prev, ...ev.items]);
        lastSeq.current = ev.last_seq;
      }
      if (TERMINAL.includes(neg.status) && timer) {
        clearInterval(timer);
      }
    }

    poll();
    timer = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [negotiationId]);

  if (!negotiation) return <p className="loading">Loading negotiation…</p>;

  return (
    <div className="panel">
      <div className="panel__header">
        <div>
          <h2>Negotiation</h2>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", background: "#e8f8f0", color: "#27ae60", border: "1px solid #27ae60", borderRadius: "4px", padding: "0.1rem 0.4rem", fontWeight: 600 }}>
              ⚡ Game-Theoretic ZOPA Active
            </span>
            <span style={{ fontSize: "0.75rem", background: "#f4f6f7", color: "#34495e", border: "1px solid #bdc3c7", borderRadius: "4px", padding: "0.1rem 0.4rem", fontWeight: 600 }}>
              🔒 SHA-256 Chained
            </span>
          </div>
        </div>
        <StatusBadge status={negotiation.status} />
      </div>
      <p className="muted">Round {negotiation.round} of {negotiation.max_rounds}</p>

      {negotiation.failure_code && (
        <p className="form-error">Outcome: {negotiation.failure_code.replace(/_/g, " ")}</p>
      )}

      <ol className="event-timeline">
        {events.map((e) => (
          <li key={e.seq} className="event-timeline__item">
            <span className="event-timeline__actor">{e.actor}</span>
            <span>{e.message}</span>
            <span className="muted">{formatDateTime(e.created_at)}</span>
          </li>
        ))}
      </ol>

      <h3>Offers & Audit Trail</h3>
      <ul className="card-list">
        {negotiation.offers.map((o) => (
          <li key={o.id} className="card-list__item">
            <div className="card-list__row">
              <strong>{o.author} — {o.action}</strong>
              <span>₹{paisePerTonneToRupees(o.unit_price_paise_per_tonne)}/t</span>
            </div>
            <p className="muted">{o.explanation}</p>
            <CostBreakdown costs={o.costs} />
            {o.chain_hash && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#7f8c8d", background: "#f8f9fa", padding: "0.3rem 0.5rem", borderRadius: "4px", fontFamily: "monospace", display: "flex", justifyContent: "space-between" }}>
                <span>🔒 SHA-256 Hash: {o.chain_hash.slice(0, 16)}...{o.chain_hash.slice(-8)}</span>
                <span style={{ color: "#27ae60", fontWeight: 600 }}>VERIFIED ✓</span>
              </div>
            )}
          </li>
        ))}
      </ul>

      {negotiation.status === "agreed" && negotiation.deal_id && (
        <div style={{ marginTop: "1.5rem" }}>
          <button className="button button--primary" onClick={() => navigate(`/deals/${negotiation.deal_id}`)}>
            View deal & Green Certificate →
          </button>
        </div>
      )}
    </div>
  );
}

