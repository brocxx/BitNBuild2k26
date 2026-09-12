import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { OwnListing } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { kgToTonnes, paisePerTonneToRupees, formatWindow } from "../utils/format";
import { DATASET_MATERIALS, getMaterialName } from "../data/datasetReference";

const EMPTY_FORM = {
  material_id: "",
  available_quantity_kg: "",
  asking_price_rupees_per_tonne: "",
  seller_floor_rupees_per_tonne: "",
  moisture_pct: "",
  contamination_notes: "",
  pickup_start: "",
  pickup_end: "",
};

export function Listings() {
  const [listings, setListings] = useState<OwnListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const res = await api.listMyListings();
    setListings(res.items);
    setLoading(false);
  }

  useEffect(() => { refresh(); }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.material_id) { setError("Select a material from the dataset first."); return; }
    setSubmitting(true);
    try {
      const me = await api.getMe();
      await api.createListing({
        material_id: form.material_id,
        available_quantity_kg: Number(form.available_quantity_kg),
        asking_price_paise_per_tonne: Math.round(Number(form.asking_price_rupees_per_tonne) * 100),
        seller_floor_paise_per_tonne: Math.round(Number(form.seller_floor_rupees_per_tonne) * 100),
        moisture_pct: Number(form.moisture_pct),
        contamination_notes: form.contamination_notes,
        pickup_window: { start: form.pickup_start, end: form.pickup_end },
        location: me.business.location,
      });
      setForm(EMPTY_FORM);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create listing.");
    } finally {
      setSubmitting(false);
    }
  }

  async function closeListing(id: string) {
    await api.updateListing(id, { status: "closed" });
    await refresh();
  }

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div>
          <span className="eyebrow">Seller workspace</span>
          <h1>List a <span className="script-accent">byproduct</span></h1>
          <p>Select the actual material and enter only the stock that is available now.</p>
        </div>
        <div className="hero-badge">Dataset materials + seller-entered stock</div>
      </section>

      <div className="two-column">
        <section className="panel panel--flush">
          <div className="section-heading">
            <div><span className="eyebrow">New listing</span><h2>What is available right now?</h2></div>
            <span className="evidence-tag">Seller entered</span>
          </div>

          <form className="stacked-form" onSubmit={handleSubmit}>
            <label>
              Material / byproduct
              <select required value={form.material_id} onChange={(e) => setForm({ ...form, material_id: e.target.value })}>
                <option value="">Select a material...</option>
                {DATASET_MATERIALS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <small>Material names come from the enterprise-byproduct dataset; no material is selected by default.</small>
            </label>
            <div className="dataset-note">
              <b>Important:</b> annual generation in the dataset is an estimate. The quantity below is the seller-confirmed inventory available for this listing.
            </div>
            <label>
              Available quantity now (kg)
              <input type="number" min={1} required value={form.available_quantity_kg}
                onChange={(e) => setForm({ ...form, available_quantity_kg: e.target.value })} placeholder="e.g. 2500" />
            </label>
            <div className="field-row">
              <label>
                Asking price (₹ / tonne)
                <input type="number" min={0} step="1" required value={form.asking_price_rupees_per_tonne}
                  onChange={(e) => setForm({ ...form, asking_price_rupees_per_tonne: e.target.value })} placeholder="e.g. 2800" />
              </label>
              <label>
                Minimum acceptable (₹ / tonne) <span className="private-pill">PRIVATE</span>
                <input type="number" min={0} step="1" required value={form.seller_floor_rupees_per_tonne}
                  onChange={(e) => setForm({ ...form, seller_floor_rupees_per_tonne: e.target.value })} placeholder="e.g. 2400" />
                <small>Only your seller agent uses this. Buyers never see it.</small>
              </label>
            </div>
            <label>
              Moisture (%)
              <input type="number" min={0} max={100} step="0.1" required value={form.moisture_pct}
                onChange={(e) => setForm({ ...form, moisture_pct: e.target.value })} placeholder="Enter 0 if not applicable" />
            </label>
            <label>
              Contamination / quality notes
              <input type="text" value={form.contamination_notes}
                onChange={(e) => setForm({ ...form, contamination_notes: e.target.value })} placeholder="Batch condition, contamination, preparation, test notes..." />
            </label>
            <div className="field-row">
              <label>Pickup start<input type="datetime-local" required value={form.pickup_start}
                onChange={(e) => setForm({ ...form, pickup_start: e.target.value })} /></label>
              <label>Pickup end<input type="datetime-local" required value={form.pickup_end}
                onChange={(e) => setForm({ ...form, pickup_end: e.target.value })} /></label>
            </div>
            {error && <p className="form-error">{error}</p>}
            <button className="button button--primary" type="submit" disabled={submitting}>{submitting ? "Publishing…" : "Publish listing"}</button>
          </form>
        </section>

        <section className="panel panel--flush">
          <div className="section-heading"><div><span className="eyebrow">Inventory</span><h2>Your listings</h2></div></div>
          {loading ? <p className="loading">Loading…</p> : listings.length === 0 ? (
            <div className="empty-state"><b>No active byproducts yet.</b><br/>Create a listing when a batch is actually available.</div>
          ) : (
            <ul className="card-list">
              {listings.map((l) => (
                <li key={l.id} className="card-list__item">
                  <div className="card-list__row"><strong>{kgToTonnes(l.available_quantity_kg)} t {getMaterialName(l.material_id)}</strong><StatusBadge status={l.status} /></div>
                  <p><b>₹{paisePerTonneToRupees(l.asking_price_paise_per_tonne)}/t</b> asking · {l.moisture_pct}% moisture</p>
                  <p className="muted">{formatWindow(l.pickup_window.start, l.pickup_window.end)}</p>
                  <div className="provenance-row"><span>Seller entered</span><span>Private floor protected</span></div>
                  {l.status === "open" && <button className="button button--ghost" onClick={() => closeListing(l.id)}>Close listing</button>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
