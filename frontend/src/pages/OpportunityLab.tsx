import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

export function OpportunityLab() {
  const [quantity, setQuantity] = useState(2);
  const [price, setPrice] = useState(2800);
  const [freightRate, setFreightRate] = useState(18);
  const [processing, setProcessing] = useState(300);
  const [moisture, setMoisture] = useState(12);
  const [distance, setDistance] = useState(40);
  const [disruption, setDisruption] = useState(false);

  const scenario = useMemo(() => {
    const freight = Math.round(distance * freightRate);
    const material = Math.round(quantity * price);
    const preparation = Math.round(quantity * processing);
    const total = material + freight + preparation;
    return {
      freight,
      material,
      preparation,
      total,
      perTonne: quantity > 0 ? Math.round(total / quantity) : 0,
    };
  }, [quantity, price, freightRate, processing, distance]);

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div>
          <span className="eyebrow">Agentic decision workspace</span>
          <h1>
            Opportunity <span className="script-accent">Lab</span>
          </h1>
          <p>
            Use this workspace after you have identified a real requirement and candidate exchange. Diagnose barriers,
            test interventions and model recovery actions without inventing suppliers before demand is defined.
          </p>
        </div>
        <Link className="button button--primary hero-badge" to="/requirements">
          Create requirement first →
        </Link>
      </section>

      <section className="feature-grid feature-grid--4">
        {[
          ["01", "Nearby-first discovery", "Compatible nearby suppliers are preferred once a buyer requirement has been submitted."],
          ["02", "Deal rescue", "For failed matches, surface the smallest change in price, freight, quantity, moisture or timing that restores viability."],
          ["03", "Disruption recovery", "Simulate a cancelled truck, withdrawn buyer or rejected batch and re-route to the next feasible option."],
          ["04", "Evidence layer", "Separate registry data, literature pathways, seller inputs, estimates and verified transaction history."],
        ].map(([n, t, d]) => (
          <article className="feature-tile" key={t}>
            <span>{n}</span>
            <h3>{t}</h3>
            <p>{d}</p>
          </article>
        ))}
      </section>

      <div className="content-grid content-grid--wide">
        <section className="panel panel--flush">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Interactive sensitivity simulator</span>
              <h2>What would make this deal work?</h2>
            </div>
            <span className="evidence-tag">Scenario calculation</span>
          </div>

          <div className="slider-grid">
            <label>
              Batch quantity <strong>{quantity.toFixed(1)} t</strong>
              <input type="range" min="0.5" max="10" step="0.5" value={quantity} onChange={(e) => setQuantity(+e.target.value)} />
            </label>
            <label>
              Material price <strong>₹{price}/t</strong>
              <input type="range" min="500" max="6000" step="100" value={price} onChange={(e) => setPrice(+e.target.value)} />
            </label>
            <label>
              Estimated distance <strong>{distance} km</strong>
              <input type="range" min="0" max="300" step="5" value={distance} onChange={(e) => setDistance(+e.target.value)} />
            </label>
            <label>
              Freight rate <strong>₹{freightRate}/km</strong>
              <input type="range" min="8" max="50" step="1" value={freightRate} onChange={(e) => setFreightRate(+e.target.value)} />
            </label>
            <label>
              Preparation <strong>₹{processing}/t</strong>
              <input type="range" min="0" max="2000" step="50" value={processing} onChange={(e) => setProcessing(+e.target.value)} />
            </label>
            <label>
              Moisture <strong>{moisture}%</strong>
              <input type="range" min="5" max="30" step="1" value={moisture} onChange={(e) => setMoisture(+e.target.value)} />
            </label>
          </div>

          <div className={`insight-card ${moisture > 15 ? "insight-card--warn" : ""}`}>
            <span className="insight-icon">✦</span>
            <div>
              <strong>{moisture > 15 ? "Potential preparation step required" : "Scenario cost"}</strong>
              <p>
                {moisture > 15
                  ? "If the selected buyer requires ≤15% moisture, drying is a candidate intervention. Confirm the actual buyer specification before treating it as required."
                  : `Under these user-entered assumptions, the route costs about ₹${scenario.perTonne.toLocaleString("en-IN")}/t delivered.`}
              </p>
            </div>
          </div>

          <div className="scenario-cost-grid">
            <div><small>Material</small><strong>₹{scenario.material.toLocaleString("en-IN")}</strong></div>
            <div><small>Freight</small><strong>₹{scenario.freight.toLocaleString("en-IN")}</strong></div>
            <div><small>Preparation</small><strong>₹{scenario.preparation.toLocaleString("en-IN")}</strong></div>
            <div><small>Total</small><strong>₹{scenario.total.toLocaleString("en-IN")}</strong></div>
          </div>
        </section>

        <section className="panel panel--flush">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Disruption recovery</span>
              <h2>Recover the exchange</h2>
            </div>
            <button className="button button--danger-soft" onClick={() => setDisruption(!disruption)}>
              {disruption ? "Restore route" : "Inject truck cancellation"}
            </button>
          </div>

          <div className="recovery-flow">
            <div className={`route-node ${disruption ? "route-node--failed" : ""}`}>
              <small>Selected supplier route</small>
              <strong>{disruption ? "Transport unavailable" : "Primary route"}</strong>
              <span>Chosen after requirement matching</span>
            </div>
            <div className="route-arrow">→</div>
            <div className="route-node route-node--buyer">
              <small>Buyer requirement</small>
              <strong>Technical + commercial constraints</strong>
              <span>Private limits remain protected</span>
            </div>
          </div>

          {disruption && (
            <div className="recovery-alert">
              <b>Truck cancelled.</b> The logistics broker re-checks the remaining compatible suppliers for this
              requirement and recalculates delivered cost before reopening negotiation.
            </div>
          )}
        </section>
      </div>

      <section className="panel panel--flush requirement-gate">
        <div>
          <span className="eyebrow">Supplier explorer</span>
          <h2>Find suppliers for a requirement</h2>
          <p>
            Compatibility depends on what you are sourcing. Enter your material, receiving process, quantity, moisture
            limit, delivery window and budget, and the next screen shows the suppliers that qualify for it — with the
            reason any others were ruled out.
          </p>
        </div>
        <Link className="button button--primary" to="/requirements">
          Enter requirement →
        </Link>
      </section>

      <section className="panel panel--flush">
        <span className="eyebrow">Roadmap</span>
        <h2>Where the exchange goes next</h2>
        <p>
          Not yet available. These build on the same dataset and agent layer as the exchange above.
        </p>
      </section>

      <section className="mini-feature-grid">
        {[
          "Small-load pooling",
          "Preparation pathways",
          "Material passport + QR",
          "Sample before bulk",
          "Recurring agreements",
          "Expiring-stock rescue",
          "Backhaul opportunities",
          "Negotiation replay",
          "Circularity receipt",
          "Overlooked partner discovery",
          "Industrial cluster map",
          "Kannada / English voice listing",
        ].map((x, i) => (
          <div className="mini-feature" key={x}>
            <span>{String(i + 1).padStart(2, "0")}</span>
            <strong>{x}</strong>
            <small>Planned</small>
          </div>
        ))}
      </section>
    </div>
  );
}
