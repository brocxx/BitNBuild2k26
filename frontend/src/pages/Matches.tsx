import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { MatchesResponse, OwnRequirement } from "../api";
import { kgToTonnes, paiseToRupees, paisePerTonneToRupees, metersToKm } from "../utils/format";
import { getMaterialName, getPathwayByProcessId } from "../data/datasetReference";

export function Matches() {
  const { requirementId } = useParams<{ requirementId: string }>();
  const navigate = useNavigate();
  const [matches, setMatches] = useState<MatchesResponse | null>(null);
  const [requirement, setRequirement] = useState<OwnRequirement | null>(null);
  const [loading, setLoading] = useState(true);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!requirementId) return;
    Promise.all([api.getMatches(requirementId), api.getRequirement(requirementId)])
      .then(([m, r]) => { setMatches(m); setRequirement(r); setLoading(false); })
      .catch((err) => { setError(err instanceof Error ? err.message : "Could not load opportunities."); setLoading(false); });
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

  if (loading) return <p className="loading">Analysing your requirement against compatible suppliers…</p>;
  if (!matches || !requirement) return <p className="empty-state">No opportunities found.</p>;

  const pathway = getPathwayByProcessId(requirement.receiving_process_id);

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div>
          <span className="eyebrow">Requirement results</span>
          <h1>{getMaterialName(requirement.material_id)} <span className="script-accent">suppliers</span></h1>
          <p>{pathway?.receiver_industry ?? requirement.receiving_process_id.replace(/_/g, " ")} · {kgToTonnes(requirement.quantity_kg)} t required · nearby compatible supply is ranked first.</p>
        </div>
        <div className="hero-badge">Budget ₹{paiseToRupees(requirement.buyer_max_total_paise)}</div>
      </section>

      {pathway && <section className="dataset-note"><b>Dataset pathway:</b> {pathway.use_case}</section>}
      {error && <p className="form-error">{error}</p>}

      {matches.candidates.length === 0 ? (
        <section className="panel panel--flush empty-state-box">
          <h2>No immediately viable supplier</h2>
          <p>No current listing passed the material, quantity, quality and timing checks for this requirement.</p>
          <Link className="button button--primary" to="/opportunities">What would make this deal work? →</Link>
        </section>
      ) : (
        <section className="panel panel--flush">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Matched after requirement submission</span>
              <h2>Nearby compatible suppliers</h2>
              <p>Rows come from the match API for the requirement you just entered; they are not a static demo table.</p>
            </div>
            <span className="evidence-tag">Nearby first</span>
          </div>
          <div className="opportunity-table">
            <div className="opportunity-row opportunity-row--head opportunity-row--matches">
              <span>Supplier</span><span>District</span><span>Distance</span><span>Available now</span><span>Asking price</span><span>Delivered total</span><span></span>
            </div>
            {matches.candidates.map((c, index) => {
              const t = c.transport_options[0];
              return (
                <div className={`opportunity-row opportunity-row--matches ${index === 0 ? "opportunity-row--best" : ""}`} key={c.listing.id}>
                  <span><b>{c.listing.seller.name}</b><small>{c.listing.seller.enterprise_id ?? "Registry enterprise"}</small></span>
                  <span>{c.listing.location.district}</span>
                  <span>{t ? metersToKm(t.distance_m) : "No route"}<small>{t ? "district estimate" : "transport needed"}</small></span>
                  <span>{kgToTonnes(c.listing.available_quantity_kg)} t<small>seller-entered stock</small></span>
                  <span>₹{paisePerTonneToRupees(c.listing.asking_price_paise_per_tonne)}/t<small>{c.listing.moisture_pct}% moisture</small></span>
                  <span>₹{paiseToRupees(c.initial_best_cost.buyer_total_paise)}<small>material + freight</small></span>
                  <span>
                    {index === 0 && <b className="rank-badge">Best nearby</b>}
                    <button className="button button--primary button--table" onClick={() => startNegotiation(c.listing.id)} disabled={startingId === c.listing.id || c.transport_options.length === 0}>
                      {startingId === c.listing.id ? "Starting…" : "Negotiate"}
                    </button>
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {matches.excluded.length > 0 && (
        <section className="panel panel--flush">
          <div className="section-heading"><div><span className="eyebrow">Barrier diagnosis</span><h2>Why some listings were excluded</h2></div></div>
          <ul>{matches.excluded.map((e) => <li key={e.listing_id}>{e.listing_id}: {e.reason_codes.join(", ").replace(/_/g, " ")}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
