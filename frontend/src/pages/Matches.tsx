import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { MatchesResponse } from "../api";
import { CostBreakdown } from "../components/CostBreakdown";
import { kgToTonnes, paisePerTonneToRupees, formatWindow, metersToKm } from "../utils/format";

export function Matches() {
  const { requirementId } = useParams<{ requirementId: string }>();
  const navigate = useNavigate();
  const [matches, setMatches] = useState<MatchesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!requirementId) return;
    api.getMatches(requirementId).then((res) => { setMatches(res); setLoading(false); });
  }, [requirementId]);

  async function startNegotiation(listingId: string) {
    if (!requirementId) return;
    setError(null); setStartingId(listingId);
    try {
      const idempotencyKey = `${requirementId}:${listingId}:${Date.now()}`;
      const res = await api.startNegotiation({ requirement_id: requirementId, listing_ids: [listingId] }, idempotencyKey);
      navigate(`/negotiations/${res.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start negotiation."); setStartingId(null);
    }
  }

  if (loading) return <p className="loading">Analysing compatible suppliers…</p>;
  if (!matches) return <p className="empty-state">No opportunities found.</p>;

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div><span className="eyebrow">Opportunity analysis</span><h1>Compatible <span className="script-accent">supply</span></h1><p>Technical fit first. Among feasible sellers, the agent gives preference to nearby supply before comparing delivered economics and negotiation room.</p></div>
        <div className="hero-badge">Nearby-first ranking</div>
      </section>

      <section className="decision-rule">
        <span>1</span><b>Pathway fit</b><i>→</i><span>2</span><b>Quality + quantity</b><i>→</i><span>3</span><b>Nearby supplier</b><i>→</i><span>4</span><b>Delivered cost</b>
      </section>

      {error && <p className="form-error">{error}</p>}
      {matches.candidates.length === 0 ? (
        <section className="panel panel--flush empty-state-box">
          <h2>No immediately viable seller</h2>
          <p>Don’t stop at “no match”. Use the intervention simulator to find the smallest change that could make the exchange feasible.</p>
          <Link className="button button--primary" to="/opportunities">What would make this deal work? →</Link>
        </section>
      ) : (
        <div className="match-grid">
          {matches.candidates.map((c, index) => {
            const t = c.transport_options[0];
            return <article key={c.listing.id} className={`match-card-new ${index === 0 ? "match-card-new--best" : ""}`}>
              <div className="match-rank">{index === 0 ? "BEST NEARBY" : `ALTERNATIVE ${index}`}</div>
              <div className="match-card-head"><div><span className="eyebrow">{c.listing.location.district}</span><h2>{c.listing.seller.name}</h2><small>{c.listing.seller.enterprise_id}</small></div><div className="distance-bubble">{t ? metersToKm(t.distance_m) : "No route"}<small>district estimate</small></div></div>

              <div className="provenance-row"><span>Registry enterprise</span><span>Dataset-supported pathway</span><span>Seller-entered stock</span></div>

              <div className="spec-grid">
                <div><small>Available now</small><b>{kgToTonnes(c.listing.available_quantity_kg)} t</b></div>
                <div><small>Asking</small><b>₹{paisePerTonneToRupees(c.listing.asking_price_paise_per_tonne)}/t</b></div>
                <div><small>Moisture</small><b>{c.listing.moisture_pct}%</b></div>
                <div><small>Use</small><b>{c.pathway_use.replace(/_/g, " ")}</b></div>
              </div>

              <div className="why-match">
                <b>Why this opportunity works</b>
                <ul><li>Rice husk → brick kiln fuel is a dataset-supported industrial-symbiosis pathway.</li><li>Current listing can cover the requested quantity.</li><li>Moisture is within the buyer threshold.</li>{index === 0 && <li>This is the nearest compatible candidate in the demo ranking.</li>}</ul>
              </div>

              <p className="muted">Pickup: {formatWindow(c.listing.pickup_window.start, c.listing.pickup_window.end)}</p>
              {t && <div className="transport-option"><div><b>{t.label}</b><small>{t.source === "configured_estimate" ? "Estimated logistics cost · demo input" : "Entered carrier quote"}</small></div><span>{metersToKm(t.distance_m)}</span></div>}
              <CostBreakdown costs={c.initial_best_cost} />

              <div className="match-actions">
                <button className="button button--primary" onClick={() => startNegotiation(c.listing.id)} disabled={startingId === c.listing.id || c.transport_options.length === 0}>{startingId === c.listing.id ? "Starting agents…" : "Start agent negotiation"}</button>
                <Link className="button button--ghost" to="/opportunities">Simulate changes</Link>
              </div>
            </article>;
          })}
        </div>
      )}

      {matches.excluded.length > 0 && <section className="panel panel--flush"><div className="section-heading"><div><span className="eyebrow">Barrier diagnosis</span><h2>Why some listings were excluded</h2></div></div><ul>{matches.excluded.map(e => <li key={e.listing_id}>{e.listing_id}: {e.reason_codes.join(", ").replace(/_/g," ")}</li>)}</ul></section>}
    </div>
  );
}
