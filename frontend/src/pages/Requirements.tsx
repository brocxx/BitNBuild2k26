import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { OwnRequirement } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { kgToTonnes, paiseToRupees, formatWindow } from "../utils/format";
import {
  DATASET_MATERIALS,
  DATASET_PATHWAYS,
  getMaterialName,
  getPathwayByProcessId,
} from "../data/datasetReference";
import { NegotiationStrategySelector } from "../components/NegotiationStrategySelector";
import type { NegotiationStrategy } from "../api";

const EMPTY_FORM = {
  material_id: "",
  receiving_process_id: "",
  quantity_kg: "",
  max_moisture_pct: "",
  buyer_max_total_rupees: "",
  delivery_start: "",
  delivery_end: "",
};

export function Requirements() {
  const navigate = useNavigate();
  const [requirements, setRequirements] = useState<OwnRequirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [strategy, setStrategy] = useState<NegotiationStrategy>("conceder");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pathways = useMemo(
    () => DATASET_PATHWAYS.filter((p) => p.material_id === form.material_id),
    [form.material_id]
  );

  async function refresh() {
    const res = await api.listMyRequirements();
    setRequirements(res.items);
    setLoading(false);
  }

  useEffect(() => { refresh(); }, []);

  function chooseMaterial(materialId: string) {
    setForm((current) => ({
      ...current,
      material_id: materialId,
      receiving_process_id: "",
    }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.material_id || !form.receiving_process_id) {
      setError("Choose a material and a dataset-supported receiving industry first.");
      return;
    }
    setSubmitting(true);
    try {
      const me = await api.getMe();
      const created = await api.createRequirement({
        material_id: form.material_id,
        receiving_process_id: form.receiving_process_id,
        quantity_kg: Number(form.quantity_kg),
        max_moisture_pct: Number(form.max_moisture_pct),
        delivery_window: { start: form.delivery_start, end: form.delivery_end },
        buyer_max_total_paise: Math.round(Number(form.buyer_max_total_rupees) * 100),
        location: me.business.location,
        negotiation_strategy: strategy,
      });
      setForm(EMPTY_FORM);
      setStrategy("conceder");
      await refresh();
      navigate(`/requirements/${created.id}/matches`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create requirement.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div>
          <span className="eyebrow">Buyer workspace</span>
          <h1>Create a <span className="script-accent">requirement</span></h1>
          <p>Select what you need first. The receiving-industry choices come directly from the industrial-symbiosis pathway dataset.</p>
        </div>
        <div className="hero-badge">Nearby compatible supply first</div>
      </section>

      <div className="two-column">
        <section className="panel panel--flush">
          <div className="section-heading">
            <div><span className="eyebrow">Demand</span><h2>What material do you need?</h2></div>
            <span className="evidence-tag">Buyer entered</span>
          </div>
          <form className="stacked-form" onSubmit={handleSubmit}>
            <label>
              Material / byproduct
              <select required value={form.material_id} onChange={(e) => chooseMaterial(e.target.value)}>
                <option value="">Select a material...</option>
                {DATASET_MATERIALS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <small>Names are taken from 03_byproducts_per_enterprise.csv. Nothing is preselected.</small>
            </label>

            <label>
              Receiving industry / process
              <select
                required
                disabled={!form.material_id}
                value={form.receiving_process_id}
                onChange={(e) => setForm({ ...form, receiving_process_id: e.target.value })}
              >
                <option value="">{form.material_id ? "Select a supported receiving industry..." : "Select a material first..."}</option>
                {DATASET_PATHWAYS.map((p) => (
                  <option key={p.process_id} value={p.process_id} disabled={p.material_id !== form.material_id}>
                    {p.receiver_industry}{p.material_id !== form.material_id ? ` : for ${getMaterialName(p.material_id)}` : ""}
                  </option>
                ))}
              </select>
              <small>
                {form.material_id
                  ? `${pathways.length} dataset-supported ${pathways.length === 1 ? "pathway" : "pathways"} for ${getMaterialName(form.material_id)}.`
                  : "The options are derived from 04_industrial_symbiosis_pairs.csv."}
              </small>
            </label>

            {form.receiving_process_id && (
              <div className="dataset-note">
                <b>Dataset use case:</b> {getPathwayByProcessId(form.receiving_process_id)?.use_case}
              </div>
            )}

            <div className="field-row">
              <label>Required quantity (kg)<input type="number" min={1} required value={form.quantity_kg} onChange={(e) => setForm({ ...form, quantity_kg: e.target.value })} placeholder="e.g. 2000" /></label>
              <label>Maximum moisture (%)<input type="number" min={0} max={100} step="0.1" required value={form.max_moisture_pct} onChange={(e) => setForm({ ...form, max_moisture_pct: e.target.value })} placeholder="e.g. 15" /></label>
            </div>
            <label>Maximum delivered budget (₹ total) <span className="private-pill">PRIVATE</span>
              <input type="number" min={0} step="1" required value={form.buyer_max_total_rupees} onChange={(e) => setForm({ ...form, buyer_max_total_rupees: e.target.value })} placeholder="e.g. 7000" />
              <small>Your buyer agent uses this limit; sellers never see it.</small>
            </label>
            <NegotiationStrategySelector value={strategy} onChange={setStrategy} />
            <div className="field-row">
              <label>Delivery start<input type="datetime-local" required value={form.delivery_start} onChange={(e) => setForm({ ...form, delivery_start: e.target.value })} /></label>
              <label>Delivery end<input type="datetime-local" required value={form.delivery_end} onChange={(e) => setForm({ ...form, delivery_end: e.target.value })} /></label>
            </div>
            {error && <p className="form-error">{error}</p>}
            <button className="button button--primary" type="submit" disabled={submitting}>{submitting ? "Analysing…" : "Find compatible suppliers"}</button>
          </form>
        </section>

        <section className="panel panel--flush">
          <div className="section-heading"><div><span className="eyebrow">Open demand</span><h2>Your requirements</h2></div></div>
          {loading ? <p className="loading">Loading…</p> : requirements.length === 0 ? (
            <div className="empty-state">No requirements posted yet. Submit the form to generate your first supplier analysis.</div>
          ) : (
            <ul className="card-list">
              {requirements.map((r) => {
                const pathway = getPathwayByProcessId(r.receiving_process_id);
                return <li key={r.id} className="card-list__item">
                  <div className="card-list__row"><strong>{kgToTonnes(r.quantity_kg)} t {getMaterialName(r.material_id)}</strong><StatusBadge status={r.status} /></div>
                  <p>{pathway?.receiver_industry ?? r.receiving_process_id.replace(/_/g, " ")} · max {r.max_moisture_pct}% moisture</p>
                  <p className="muted">{formatWindow(r.delivery_window.start, r.delivery_window.end)}</p>
                  <p><span className="private-pill">PRIVATE</span> Budget ₹{paiseToRupees(r.buyer_max_total_paise)}</p>
                  {r.status === "open" && <Link className="button button--primary" to={`/requirements/${r.id}/matches`}>View matched suppliers →</Link>}
                </li>;
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
