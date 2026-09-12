import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { GreenCertificate } from "../api";
import { formatDateTime, kgToTonnes } from "../utils/format";

export function ESGCertificate() {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const [cert, setCert] = useState<GreenCertificate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dealId) return;
    setLoading(true);
    api
      .getDealCertificate(dealId)
      .then((res) => {
        setCert(res);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message || "Failed to load green certificate");
        setLoading(false);
      });
  }, [dealId]);

  if (loading) {
    return (
      <div className="panel" style={{ maxWidth: "800px", margin: "2rem auto", textAlign: "center" }}>
        <p className="loading">Generating Digital Green Certificate…</p>
      </div>
    );
  }

  if (error || !cert) {
    return (
      <div className="panel" style={{ maxWidth: "800px", margin: "2rem auto" }}>
        <h2>Certificate Unavailable</h2>
        <p className="form-error">{error || "Certificate could not be loaded."}</p>
        <button
          type="button"
          className="button button--secondary"
          onClick={() => navigate(`/deals/${dealId}`)}
        >
          ← Back to Deal
        </button>
      </div>
    );
  }

  const esg = cert.esg_metrics;

  return (
    <div className="certificate-wrapper" style={{ maxWidth: "880px", margin: "1.5rem auto" }}>
      <div className="certificate-actions no-print" style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <button
          type="button"
          className="button button--ghost"
          onClick={() => navigate(`/deals/${dealId}`)}
        >
          ← Back to Deal
        </button>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            className="button button--primary"
            onClick={() => window.print()}
          >
            ⬇ Download / Print PDF
          </button>
        </div>
      </div>

      <div
        className="certificate-card"
        style={{
          border: "2px solid #27ae60",
          borderRadius: "12px",
          padding: "2.5rem",
          background: "var(--color-surface, #ffffff)",
          boxShadow: "0 10px 30px rgba(39, 174, 96, 0.12)",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "1.5rem",
            right: "1.5rem",
            background: "#e8f8f0",
            color: "#27ae60",
            border: "1px solid #27ae60",
            borderRadius: "6px",
            padding: "0.25rem 0.75rem",
            fontSize: "0.85rem",
            fontWeight: 700,
          }}
        >
          VERIFIED BY KIB ✓
        </div>

        <div style={{ textAlign: "center", borderBottom: "2px dashed #dcdde1", paddingBottom: "1.5rem", marginBottom: "2rem" }}>
          <div style={{ fontSize: "2.2rem", marginBottom: "0.25rem" }}>🌿</div>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0", color: "#27ae60", letterSpacing: "1px" }}>
            DIGITAL GREEN CERTIFICATE
          </h1>
          <p style={{ margin: "0.25rem 0", color: "#7f8c8d", fontSize: "0.95rem", fontWeight: 600 }}>
            {cert.issuer}
          </p>
          <p style={{ margin: "0.25rem 0", fontSize: "0.85rem", fontFamily: "monospace", color: "#34495e" }}>
            Certificate ID: <strong>{cert.certificate_id}</strong>
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "2rem" }}>
          <div style={{ background: "#f8f9fa", padding: "1.2rem", borderRadius: "8px" }}>
            <span style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "#95a5a6", fontWeight: 700 }}>
              SUPPLIER (BYPRODUCT GENERATOR)
            </span>
            <h3 style={{ margin: "0.35rem 0 0.15rem 0", fontSize: "1.1rem" }}>{cert.seller.name}</h3>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "#7f8c8d" }}>
              District: <strong>{cert.seller.location.district}</strong>
            </p>
          </div>

          <div style={{ background: "#f8f9fa", padding: "1.2rem", borderRadius: "8px" }}>
            <span style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "#95a5a6", fontWeight: 700 }}>
              RECEIVER (SECONDARY USER)
            </span>
            <h3 style={{ margin: "0.35rem 0 0.15rem 0", fontSize: "1.1rem" }}>{cert.buyer.name}</h3>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "#7f8c8d" }}>
              District: <strong>{cert.buyer.location.district}</strong>
            </p>
          </div>
        </div>

        <div style={{ background: "#fdfefe", border: "1px solid #eaeded", borderRadius: "8px", padding: "1.2rem", marginBottom: "2rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", textAlign: "center" }}>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Material Exchanged</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, marginTop: "0.25rem" }}>
                {cert.material_display_name}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Quantity Diverted</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, marginTop: "0.25rem" }}>
                {kgToTonnes(cert.quantity_kg)} tonnes ({cert.quantity_kg.toLocaleString("en-IN")} kg)
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Transport Route</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, marginTop: "0.25rem" }}>
                {cert.transport_distance_km} km
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#7f8c8d" }}>Trade Settlement Date</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, marginTop: "0.25rem" }}>
                {formatDateTime(cert.trade_date)}
              </div>
            </div>
          </div>
        </div>

        <h3 style={{ fontSize: "1.15rem", marginBottom: "1rem", color: "#2c3e50" }}>
          Verified Environmental Impact
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
          <div style={{ background: "#e8f8f0", border: "1px solid #a3e4d7", borderRadius: "8px", padding: "1.2rem", textAlign: "center" }}>
            <div style={{ fontSize: "0.85rem", color: "#16a085", fontWeight: 600 }}>Net CO₂e Avoided</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#27ae60", margin: "0.25rem 0" }}>
              {(esg.net_co2e_avoided_kg / 1000).toFixed(2)} <span style={{ fontSize: "0.95rem" }}>tonnes</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "#7f8c8d" }}>
              {esg.net_co2e_avoided_kg.toLocaleString("en-IN")} kg net reduction
            </div>
          </div>

          <div style={{ background: "#eaf2f8", border: "1px solid #aed6f1", borderRadius: "8px", padding: "1.2rem", textAlign: "center" }}>
            <div style={{ fontSize: "0.85rem", color: "#2980b9", fontWeight: 600 }}>Landfill Diverted</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#2980b9", margin: "0.25rem 0" }}>
              {(esg.landfill_diverted_kg / 1000).toFixed(2)} <span style={{ fontSize: "0.95rem" }}>tonnes</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "#7f8c8d" }}>
              100% circular byproduct recovery
            </div>
          </div>

          <div style={{ background: "#fef9e7", border: "1px solid #f9e79f", borderRadius: "8px", padding: "1.2rem", textAlign: "center" }}>
            <div style={{ fontSize: "0.85rem", color: "#d4ac0d", fontWeight: 600 }}>Carbon Credits Equivalent</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#b7950b", margin: "0.25rem 0" }}>
              {esg.carbon_credits_estimated.toFixed(3)} <span style={{ fontSize: "0.95rem" }}>tCO₂e</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "#7f8c8d" }}>
              Standard VCS / Gold Standard units
            </div>
          </div>
        </div>

        <div style={{ background: "#fafafa", borderRadius: "8px", padding: "1rem", fontSize: "0.85rem", color: "#7f8c8d", marginBottom: "1.5rem" }}>
          <p style={{ margin: "0.2rem 0" }}>
            <strong>Virgin Raw Material Replaced:</strong> {esg.replaces_virgin} (Gross Avoided: {(esg.gross_co2e_avoided_kg / 1000).toFixed(2)} tonnes CO₂e)
          </p>
          <p style={{ margin: "0.2rem 0" }}>
            <strong>Freight Footprint Deducted:</strong> {(esg.transport_co2e_kg / 1000).toFixed(2)} tonnes CO₂e ({esg.transport_co2e_kg.toFixed(1)} kg)
          </p>
          <p style={{ margin: "0.2rem 0" }}>
            <strong>Methodology Standard:</strong> {cert.methodology}
          </p>
        </div>

        <div style={{ borderTop: "1px solid #eaeded", paddingTop: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem", color: "#95a5a6" }}>
          <div>
            Cryptographic SHA-256 Audit Fingerprint:<br />
            <code style={{ fontSize: "0.75rem", color: "#2c3e50" }}>{cert.verification_hash}</code>
          </div>
          <div style={{ textAlign: "right" }}>
            Karnataka Circular Economy Authority<br />
            <strong>Official Digital Green Ledger</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
