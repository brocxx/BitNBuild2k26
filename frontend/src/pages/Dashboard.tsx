import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Business, Deal, NegotiationSummary, OwnListing, OwnRequirement } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { kgToTonnes, paisePerTonneToRupees, formatDateTime } from "../utils/format";
import { getMaterialName, getPathwayByProcessId } from "../data/datasetReference";

export function Dashboard() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [listings, setListings] = useState<OwnListing[]>([]);
  const [requirements, setRequirements] = useState<OwnRequirement[]>([]);
  const [negotiations, setNegotiations] = useState<NegotiationSummary[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getMe().catch(() => null),
      api.listMyListings().catch(() => ({ items: [], next_cursor: null })),
      api.listMyRequirements().catch(() => ({ items: [], next_cursor: null })),
      api.listMyNegotiations().catch(() => ({ items: [], next_cursor: null })),
      api.listMyDeals().catch(() => ({ items: [], next_cursor: null })),
    ]).then(([me, l, r, n, d]) => {
      if (cancelled) return;
      if (me?.business) setBusiness(me.business);
      setListings(l.items);
      setRequirements(r.items);
      setNegotiations(n.items);
      setDeals(d.items);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const openReqs = useMemo(() => requirements.filter((r) => r.status === "open"), [requirements]);
  const activeNegs = useMemo(
    () => negotiations.filter((n) => n.status === "running" || n.status === "queued").length,
    [negotiations]
  );
  const diverted = useMemo(
    () => deals.filter((d) => d.status !== "cancelled").reduce((sum, d) => sum + d.quantity_kg, 0) / 1000,
    [deals]
  );

  const firstOpenReq = openReqs[0];

  if (loading) {
    return (
      <div className="skeleton-page">
        <div className="skeleton skeleton--hero" />
        <div className="metric-grid">
          {[1, 2, 3, 4].map((i) => (
            <div className="skeleton skeleton--card" key={i} />
          ))}
        </div>
      </div>
    );
  }

  const locationDisplay = business?.location.district || "Karnataka";
  const activePathway = firstOpenReq ? getPathwayByProcessId(firstOpenReq.receiving_process_id) : undefined;

  return (
    <div className="page-stack dashboard">
      <section className="hero-card">
        <div className="hero-copy">
          <span className="eyebrow">Circular material intelligence</span>
          <h1>Good evening</h1>
          <p>
            {business?.name ? `${business.name} · ${locationDisplay}. ` : ""}Turn industrial byproducts into dependable supply.
            Create a requirement first, then compare only the suppliers compatible with that material and receiving pathway.
          </p>
          <div className="hero-actions">
            <Link className="button button--primary" to="/listings">
              + List a byproduct
            </Link>
            <Link className="button button--soft" to="/requirements">
              Create requirement
            </Link>
            <Link className="button button--ghost" to="/opportunities">
              Open Opportunity Lab
            </Link>
          </div>
          <div className="hero-meta">
            <span>Dataset-backed pathways</span>
            <span>Nearby-first ranking</span>
            <span>Private agent limits</span>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit-ring orbit-ring--1"></div>
          <div className="orbit-ring orbit-ring--2"></div>
          <div className="orbit-core">KIB</div>
          <span className="orbit-dot orbit-dot--1">Supplier</span>
          <span className="orbit-dot orbit-dot--2">Buyer</span>
          <span className="orbit-dot orbit-dot--3">Broker</span>
        </div>
      </section>

      <section className="metric-grid">
        <article className="metric-card">
          <span className="metric-kicker">Open listings</span>
          <strong>{listings.filter((l) => l.status === "open").length}</strong>
          <small>Live seller-entered inventory</small>
        </article>
        <article className="metric-card">
          <span className="metric-kicker">Requirements</span>
          <strong>{openReqs.length}</strong>
          <small>Buyer demand waiting for supply</small>
        </article>
        <article className="metric-card">
          <span className="metric-kicker">Agent activity</span>
          <strong>{activeNegs}</strong>
          <small>Negotiations currently active</small>
        </article>
        <article className="metric-card metric-card--accent">
          <span className="metric-kicker">Material diverted</span>
          <strong>{diverted.toFixed(1)} t</strong>
          <small>From agreed transactions</small>
        </article>
      </section>

      <section className="content-grid content-grid--wide">
        <div className="panel panel--flush opportunity-highlight">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Compatible supply</span>
              <h2>{firstOpenReq ? `${getMaterialName(firstOpenReq.material_id)}: ${activePathway?.receiver_industry ?? "selected pathway"}` : "Start with a buyer requirement"}</h2>
            </div>
            {firstOpenReq && <span className="evidence-tag">Active requirement</span>}
          </div>

          {firstOpenReq ? (
            <>
              <div className="pathway-flow">
                <div className="pathway-node">
                  <small>Requested material</small>
                  <strong>{getMaterialName(firstOpenReq.material_id)}</strong>
                  <span>{kgToTonnes(firstOpenReq.quantity_kg)} t required</span>
                </div>
                <div className="pathway-line"><span>Match</span>→</div>
                <div className="pathway-node pathway-node--buyer">
                  <small>Receiving industry</small>
                  <strong>{activePathway?.receiver_industry ?? firstOpenReq.receiving_process_id.replace(/_/g, " ")}</strong>
                  <span>{locationDisplay}</span>
                </div>
              </div>
              <p className="fine-print">Supplier ranking is generated only after this requirement exists.</p>
              <div className="hero-actions">
                <Link className="button button--primary" to={`/requirements/${firstOpenReq.id}/matches`}>
                  View compatible suppliers →
                </Link>
              </div>
            </>
          ) : (
            <div className="empty-state">
              No material is assumed by default. Select a byproduct, receiving industry, quantity and budget first; then the nearby-supplier table is generated from that requirement.
              <div className="hero-actions">
                <Link className="button button--primary" to="/requirements">Create requirement →</Link>
              </div>
            </div>
          )}
        </div>

        <div className="panel panel--flush agent-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Agent layer</span>
              <h2>Three agents, one deal</h2>
            </div>
            <span className="live-dot">● Ready</span>
          </div>
          <div className="agent-list">
            <div>
              <span className="agent-icon">B</span>
              <p>
                <b>Buyer agent</b>
                <small>Budget, specs, timing</small>
              </p>
            </div>
            <div>
              <span className="agent-icon">S</span>
              <p>
                <b>Seller agent</b>
                <small>Floor price, stock, pickup</small>
              </p>
            </div>
            <div>
              <span className="agent-icon">L</span>
              <p>
                <b>Logistics broker</b>
                <small>Distance, quote, delivery</small>
              </p>
            </div>
          </div>
          <div className="privacy-callout">
            <b>Commercial boundaries stay private.</b>
            <span>Only proposed terms are shared with the counterparty.</span>
          </div>
        </div>
      </section>

      <section className="panel panel--flush">
        <div className="section-heading">
          <div>
            <span className="eyebrow">What makes this more than a marketplace</span>
            <h2>Barrier-solving features</h2>
          </div>
          <Link className="text-link" to="/opportunities">
            Explore all →
          </Link>
        </div>
        <div className="feature-grid feature-grid--4">
          <article className="feature-tile">
            <span>01</span>
            <h3>Nearby-first discovery</h3>
            <p>Compatible nearby suppliers are considered first before farther alternatives.</p>
          </article>
          <article className="feature-tile">
            <span>02</span>
            <h3>What would make this work?</h3>
            <p>Failed deals return actionable changes in price, freight, quantity, moisture or timing.</p>
          </article>
          <article className="feature-tile">
            <span>03</span>
            <h3>Disruption recovery</h3>
            <p>Inject a truck cancellation or rejected batch and recover with the next viable route.</p>
          </article>
          <article className="feature-tile">
            <span>04</span>
            <h3>Evidence layer</h3>
            <p>Separate dataset evidence, user inputs, estimates and calculated outputs.</p>
          </article>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel panel--flush">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Inventory</span>
              <h2>Current listings</h2>
            </div>
            <Link className="text-link" to="/listings">
              Manage →
            </Link>
          </div>
          {listings.length === 0 ? (
            <div className="empty-state">No listings yet.</div>
          ) : (
            <div className="compact-list">
              {listings.slice(0, 3).map((l) => (
                <div className="compact-row" key={l.id}>
                  <div>
                    <b>{getMaterialName(l.material_id)}</b>
                    <small>
                      {kgToTonnes(l.available_quantity_kg)} t · {l.moisture_pct}% moisture
                    </small>
                  </div>
                  <div className="compact-right">
                    <b>₹{paisePerTonneToRupees(l.asking_price_paise_per_tonne)}/t</b>
                    <StatusBadge status={l.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel panel--flush">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Activity</span>
              <h2>Recent negotiations</h2>
            </div>
          </div>
          {negotiations.length === 0 ? (
            <div className="empty-state">
              No negotiations yet. Open a requirement and start with the nearest feasible supplier.
            </div>
          ) : (
            <div className="compact-list">
              {negotiations.slice(0, 4).map((n) => (
                <Link className="compact-row compact-row--link" key={n.id} to={`/negotiations/${n.id}`}>
                  <div>
                    <b>{n.id}</b>
                    <small>{formatDateTime(n.created_at)}</small>
                  </div>
                  <StatusBadge status={n.status} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
