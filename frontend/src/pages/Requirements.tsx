import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { OwnRequirement, ReferenceData } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { kgToTonnes, paiseToRupees, formatWindow } from "../utils/format";

const EMPTY_FORM = { receiving_process_id: "", quantity_kg: "", max_moisture_pct: "", buyer_max_total_rupees: "", delivery_start: "", delivery_end: "" };

export function Requirements() {
  const [requirements, setRequirements] = useState<OwnRequirement[]>([]);
  const [reference, setReference] = useState<ReferenceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [res, ref] = await Promise.all([api.listMyRequirements(), api.getReference()]);
    setRequirements(res.items); setReference(ref);
    if (!form.receiving_process_id && ref.receiving_processes.length) setForm((f) => ({ ...f, receiving_process_id: ref.receiving_processes[0].id }));
    setLoading(false);
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault(); setError(null); setSubmitting(true);
    try {
      const me = await api.getMe();
      await api.createRequirement({
        material_id: "rice_husk",
        receiving_process_id: form.receiving_process_id,
        quantity_kg: Number(form.quantity_kg),
        max_moisture_pct: Number(form.max_moisture_pct),
        delivery_window: { start: form.delivery_start, end: form.delivery_end },
        buyer_max_total_paise: Math.round(Number(form.buyer_max_total_rupees) * 100),
        location: me.business.location,
      });
      setForm({ ...EMPTY_FORM, receiving_process_id: form.receiving_process_id });
      await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create requirement."); }
    finally { setSubmitting(false); }
  }

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div><span className="eyebrow">Buyer workspace</span><h1>Create a <span className="script-accent">requirement</span></h1><p>Tell the buyer agent what your process needs and the private commercial boundary it must respect.</p></div>
        <div className="hero-badge">Nearby compatible supply first</div>
      </section>

      <div className="two-column">
        <section className="panel panel--flush">
          <div className="section-heading"><div><span className="eyebrow">Demand</span><h2>What material do you need?</h2></div><span className="evidence-tag">Buyer entered</span></div>
          <form className="stacked-form" onSubmit={handleSubmit}>
            <label>Receiving process
              <select value={form.receiving_process_id} onChange={(e) => setForm({ ...form, receiving_process_id: e.target.value })}>
                {reference?.receiving_processes.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <small>Compatibility is checked against the industrial-symbiosis pathway reference.</small>
            </label>
            <div className="field-row">
              <label>Required quantity (kg)<input type="number" min={1} required value={form.quantity_kg} onChange={(e) => setForm({ ...form, quantity_kg: e.target.value })} placeholder="e.g. 2000" /></label>
              <label>Maximum moisture (%)<input type="number" min={0} max={100} step="0.1" required value={form.max_moisture_pct} onChange={(e) => setForm({ ...form, max_moisture_pct: e.target.value })} placeholder="e.g. 15" /></label>
            </div>
            <label>Maximum delivered budget (₹ total) <span className="private-pill">PRIVATE</span>
              <input type="number" min={0} step="1" required value={form.buyer_max_total_rupees} onChange={(e) => setForm({ ...form, buyer_max_total_rupees: e.target.value })} placeholder="e.g. 7000" />
              <small>Your buyer agent uses this limit; sellers never see it.</small>
            </label>
            <div className="field-row">
              <label>Delivery start<input type="datetime-local" required value={form.delivery_start} onChange={(e) => setForm({ ...form, delivery_start: e.target.value })} /></label>
              <label>Delivery end<input type="datetime-local" required value={form.delivery_end} onChange={(e) => setForm({ ...form, delivery_end: e.target.value })} /></label>
            </div>
            {error && <p className="form-error">{error}</p>}
            <button className="button button--primary" type="submit" disabled={submitting}>{submitting ? "Posting…" : "Find circular supply"}</button>
          </form>
        </section>

        <section className="panel panel--flush">
          <div className="section-heading"><div><span className="eyebrow">Open demand</span><h2>Your requirements</h2></div></div>
          {loading ? <p className="loading">Loading…</p> : requirements.length === 0 ? <div className="empty-state">No requirements posted yet.</div> : (
            <ul className="card-list">
              {requirements.map((r) => <li key={r.id} className="card-list__item">
                <div className="card-list__row"><strong>{kgToTonnes(r.quantity_kg)} t rice husk</strong><StatusBadge status={r.status} /></div>
                <p>{r.receiving_process_id.replace(/_/g, " ")} · max {r.max_moisture_pct}% moisture</p>
                <p className="muted">{formatWindow(r.delivery_window.start, r.delivery_window.end)}</p>
                <p><span className="private-pill">PRIVATE</span> Budget ₹{paiseToRupees(r.buyer_max_total_paise)}</p>
                {r.status === "open" && <Link className="button button--primary" to={`/requirements/${r.id}/matches`}>View opportunities →</Link>}
              </li>)}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
