import { useMemo, useState } from "react";

const partners = [
  { id: "KA-ENT-000020", district: "KOLAR", industry: "Rice milling", distance: 0, annual: 20, status: "Nearest", fit: "Dataset-supported pathway" },
  { id: "KA-ENT-000089", district: "BENGALURU (URBAN)", industry: "Rice milling", distance: 60.74, annual: 20, status: "Nearby", fit: "Dataset-supported pathway" },
  { id: "KA-ENT-000478", district: "MANDYA", industry: "Rice milling", distance: 150.24, annual: 20, status: "Alternative", fit: "Dataset-supported pathway" },
  { id: "KA-ENT-000211", district: "BALLARI", industry: "Rice milling", distance: 258.06, annual: 20, status: "Fallback", fit: "Dataset-supported pathway" },
];

export function OpportunityLab() {
  const [quantity, setQuantity] = useState(2);
  const [price, setPrice] = useState(2800);
  const [freightRate, setFreightRate] = useState(18);
  const [processing, setProcessing] = useState(300);
  const [moisture, setMoisture] = useState(12);
  const [disruption, setDisruption] = useState(false);

  const viable = useMemo(() => partners.map((p) => {
    const freight = Math.round(p.distance * freightRate);
    const total = Math.round(quantity * price + freight + quantity * processing);
    return { ...p, freight, total, perTonne: Math.round(total / quantity) };
  }).sort((a,b) => disruption ? a.distance-b.distance : a.total-b.total), [quantity, price, freightRate, processing, disruption]);

  const best = viable[0];

  return <div className="page-stack">
    <section className="hero-card compact-hero">
      <div>
        <span className="eyebrow">Agentic decision workspace</span>
        <h1>Opportunity <span className="script-accent">Lab</span></h1>
        <p>Go beyond matching. Diagnose why an exchange fails, test interventions, and recover from disruptions.</p>
      </div>
      <div className="hero-badge">Rice Husk → Brick Kiln Fuel</div>
    </section>

    <section className="feature-grid feature-grid--4">
      {[
        ["01", "Nearby-first discovery", "Compatible suppliers are ranked with proximity as the first operational preference, then delivered economics."],
        ["02", "Deal rescue", "For failed matches, surface the smallest change in price, freight, quantity, moisture or timing that restores viability."],
        ["03", "Disruption recovery", "Simulate a cancelled truck, withdrawn buyer or rejected batch and re-route to the next feasible option."],
        ["04", "Evidence layer", "Separate registry data, literature pathways, seller inputs, estimates and verified transaction history."],
      ].map(([n,t,d]) => <article className="feature-tile" key={t}><span>{n}</span><h3>{t}</h3><p>{d}</p></article>)}
    </section>

    <div className="content-grid content-grid--wide">
      <section className="panel panel--flush">
        <div className="section-heading"><div><span className="eyebrow">Interactive sensitivity simulator</span><h2>What would make this deal work?</h2></div><span className="evidence-tag">Calculated</span></div>
        <div className="slider-grid">
          <label>Batch quantity <strong>{quantity.toFixed(1)} t</strong><input type="range" min="0.5" max="10" step="0.5" value={quantity} onChange={e=>setQuantity(+e.target.value)} /></label>
          <label>Material price <strong>₹{price}/t</strong><input type="range" min="500" max="6000" step="100" value={price} onChange={e=>setPrice(+e.target.value)} /></label>
          <label>Freight rate <strong>₹{freightRate}/km</strong><input type="range" min="8" max="50" step="1" value={freightRate} onChange={e=>setFreightRate(+e.target.value)} /></label>
          <label>Preparation <strong>₹{processing}/t</strong><input type="range" min="0" max="2000" step="50" value={processing} onChange={e=>setProcessing(+e.target.value)} /></label>
          <label>Moisture <strong>{moisture}%</strong><input type="range" min="5" max="30" step="1" value={moisture} onChange={e=>setMoisture(+e.target.value)} /></label>
        </div>
        <div className={`insight-card ${moisture > 15 ? "insight-card--warn" : ""}`}>
          <span className="insight-icon">✦</span>
          <div><strong>{moisture > 15 ? "Intervention recommended" : "Current pathway is technically plausible"}</strong><p>{moisture > 15 ? `Moisture exceeds the 15% receiving threshold. Drying to ≤15% is the minimum technical intervention before negotiation.` : `At the current assumptions, ${best.id} in ${best.district} is the preferred nearby route at ~₹${best.perTonne.toLocaleString("en-IN")}/t delivered.`}</p></div>
        </div>
      </section>

      <section className="panel panel--flush">
        <div className="section-heading"><div><span className="eyebrow">Live scenario</span><h2>Disruption recovery</h2></div><button className="button button--danger-soft" onClick={()=>setDisruption(!disruption)}>{disruption ? "Restore normal route" : "Inject truck cancellation"}</button></div>
        <div className="recovery-flow">
          <div className={`route-node ${disruption ? "route-node--failed" : ""}`}><small>Preferred supplier</small><strong>{partners[0].id}</strong><span>Kolar · 0 km</span></div>
          <div className="route-arrow">→</div>
          <div className="route-node route-node--buyer"><small>Buyer</small><strong>KA-ENT-000179</strong><span>Brick manufacturing · Kolar</span></div>
        </div>
        {disruption && <div className="recovery-alert"><b>Truck cancelled.</b> Logistics broker is searching alternative feasible routes. <strong>{partners[1].id}</strong> in Bengaluru Urban becomes the next nearby supplier at 60.74 km.</div>}
      </section>
    </div>

    <section className="panel panel--flush">
      <div className="section-heading"><div><span className="eyebrow">Industrial symbiosis explorer</span><h2>Nearby compatible suppliers</h2><p>Preference: compatible nearby supply first, then delivered economics and reliability.</p></div><span className="evidence-tag">District distance matrix</span></div>
      <div className="opportunity-table">
        <div className="opportunity-row opportunity-row--head"><span>Supplier</span><span>District</span><span>Distance</span><span>Est. annual generation</span><span>Delivered scenario</span><span></span></div>
        {viable.map((p, i) => <div className={`opportunity-row ${i===0 ? "opportunity-row--best" : ""}`} key={p.id}>
          <span><b>{p.id}</b><small>{p.industry}</small></span><span>{p.district}</span><span>{p.distance.toFixed(2)} km</span><span>{p.annual} t/year <small>Dataset estimate</small></span><span>₹{p.total.toLocaleString("en-IN")} <small>scenario total</small></span><span>{i===0 ? <b className="rank-badge">Best nearby</b> : <span className="muted">Alternative</span>}</span>
        </div>)}
      </div>
    </section>

    <section className="mini-feature-grid">
      {["Small-load pooling", "Preparation pathways", "Material passport + QR", "Sample before bulk", "Recurring agreements", "Expiring-stock rescue", "Backhaul opportunities", "Negotiation replay", "Circularity receipt", "Overlooked partner discovery", "Industrial cluster map", "Kannada / English voice listing"].map((x,i)=><div className="mini-feature" key={x}><span>{String(i+1).padStart(2,"0")}</span><strong>{x}</strong><small>{[1,2,5,6,9].includes(i) ? "Core-ready" : "Prototype extension"}</small></div>)}
    </section>
  </div>;
}
