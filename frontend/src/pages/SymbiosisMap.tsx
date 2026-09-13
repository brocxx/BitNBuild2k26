import { useCallback, useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api";
import type { Deal, MapEnterprise } from "../api";
import { DATASET_PATHWAYS, getMaterialName } from "../data/datasetReference";
import {
  KARNATAKA_CENTER,
  SECTOR_COLORS,
  SECTOR_LABELS,
  countUniqueDistricts,
  jitterCoords,
  sectorColor,
} from "../utils/mapUtils";

type SymbiosisLink = {
  from: [number, number];
  to: [number, number];
  targetId: string;
};

function formatByproducts(byproducts: string[]): string {
  if (!byproducts.length) return "No byproducts on record";
  return byproducts
    .map((id) => {
      const pathway = DATASET_PATHWAYS.find((p) => p.material_id === id);
      const pct = id === "rice_husk" ? "20%" : id === "rice_bran" ? "10%" : null;
      const label = getMaterialName(id);
      return pct ? `${label} (${pct} of paddy)` : label;
    })
    .join(", ");
}

function EnterprisePopup({
  enterprise,
  onDiscover,
  discovering,
}: {
  enterprise: MapEnterprise;
  onDiscover: (enterprise: MapEnterprise) => void;
  discovering: boolean;
}) {
  const sectorLabel = SECTOR_LABELS[enterprise.sector] ?? enterprise.sector;

  return (
    <div className="map-popup">
      <strong>{enterprise.name}</strong>
      <p>
        District: {enterprise.district} | Sector: {sectorLabel} ({enterprise.sector})
      </p>
      <p>Byproducts: {formatByproducts(enterprise.byproducts)}</p>
      <button
        type="button"
        className="button button--primary button--full map-popup__action"
        disabled={discovering}
        onClick={(e) => {
          e.stopPropagation();
          onDiscover(enterprise);
        }}
      >
        {discovering ? "Searching…" : "Find Compatible Buyers within 150 km →"}
      </button>
    </div>
  );
}

export function SymbiosisMap() {
  const [enterprises, setEnterprises] = useState<MapEnterprise[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [origin, setOrigin] = useState<MapEnterprise | null>(null);
  const [symbiosisLinks, setSymbiosisLinks] = useState<SymbiosisLink[]>([]);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getMapEnterprises(), api.listMyDeals()])
      .then(([mapRes, dealsRes]) => {
        if (cancelled) return;
        setEnterprises(mapRes.enterprises);
        setDeals(dealsRes.items);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message || "Failed to load map data");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeTrades = useMemo(
    () => deals.filter((d) => d.status === "agreed"),
    [deals]
  );

  const tradeCorridors = useMemo(() => {
    return activeTrades
      .map((deal) => {
        const sellerLat = deal.seller.location.lat;
        const sellerLon = deal.seller.location.lon;
        const buyerLat = deal.buyer.location.lat;
        const buyerLon = deal.buyer.location.lon;
        if (
          sellerLat == null ||
          sellerLon == null ||
          buyerLat == null ||
          buyerLon == null
        ) {
          return null;
        }
        return {
          id: deal.id,
          positions: [
            [sellerLat, sellerLon],
            [buyerLat, buyerLon],
          ] as [number, number][],
        };
      })
      .filter(Boolean) as { id: string; positions: [number, number][] }[];
  }, [activeTrades]);

  const enterprisePositions = useMemo(() => {
    const map = new Map<string, [number, number]>();
    for (const e of enterprises) {
      map.set(e.enterprise_id, jitterCoords(e.enterprise_id, e.lat, e.lon));
    }
    return map;
  }, [enterprises]);

  const handleDiscover = useCallback(
    async (enterprise: MapEnterprise) => {
      setDiscovering(true);
      setOrigin(enterprise);
      setError(null);
      try {
        const result = await api.getSymbiosisNeighbors(enterprise.district, 150);
        const from = enterprisePositions.get(enterprise.enterprise_id) ?? [
          enterprise.lat,
          enterprise.lon,
        ];
        const links: SymbiosisLink[] = [];
        const ids = new Set<string>();

        for (const target of result.compatible_enterprises) {
          ids.add(target.enterprise_id);
          const to = enterprisePositions.get(target.enterprise_id) ?? [
            target.lat,
            target.lon,
          ];
          links.push({ from, to, targetId: target.enterprise_id });
        }

        setHighlightedIds(ids);
        setSymbiosisLinks(links);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Symbiosis search failed");
        setSymbiosisLinks([]);
        setHighlightedIds(new Set());
      } finally {
        setDiscovering(false);
      }
    },
    [enterprisePositions]
  );

  const clearSymbiosis = () => {
    setOrigin(null);
    setSymbiosisLinks([]);
    setHighlightedIds(new Set());
  };

  if (loading) {
    return (
      <div className="map-page">
        <p className="loading">Loading geospatial map…</p>
      </div>
    );
  }

  const districtCount = countUniqueDistricts(enterprises);

  return (
    <div className="map-page">
      <div className="map-page__header">
        <div>
          <div className="eyebrow">Geospatial symbiosis</div>
          <h2>Karnataka industrial map</h2>
          <p>
            {enterprises.length.toLocaleString("en-IN")} real UDYAM enterprises with
            district-level coordinates from the Karnataka MSME dataset.
          </p>
        </div>
        {origin && (
          <button type="button" className="button button--ghost" onClick={clearSymbiosis}>
            Clear symbiosis overlay
          </button>
        )}
      </div>

      <div className="map-stats-bar">
        <span>
          <strong>{enterprises.length.toLocaleString("en-IN")}</strong> Real Enterprises
        </span>
        <span className="map-stats-bar__sep">|</span>
        <span>
          <strong>{districtCount}</strong> Districts
        </span>
        <span className="map-stats-bar__sep">|</span>
        <span>
          <strong>{DATASET_PATHWAYS.length}</strong> Symbiosis Pathways
        </span>
        <span className="map-stats-bar__sep">|</span>
        <span>
          <strong>{activeTrades.length}</strong> Active Trades
        </span>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="map-layout">
        <div className="map-container-wrap">
          <MapContainer
            center={[KARNATAKA_CENTER.lat, KARNATAKA_CENTER.lon]}
            zoom={KARNATAKA_CENTER.zoom}
            className="symbiosis-map"
            preferCanvas
            scrollWheelZoom
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {enterprises.map((enterprise) => {
              const pos = enterprisePositions.get(enterprise.enterprise_id)!;
              const color = sectorColor(enterprise.sector);
              const isHighlighted = highlightedIds.has(enterprise.enterprise_id);
              const isOrigin = origin?.enterprise_id === enterprise.enterprise_id;
              const radius = isOrigin ? 7 : isHighlighted ? 6 : 4;

              return (
                <CircleMarker
                  key={enterprise.enterprise_id}
                  center={pos}
                  radius={radius}
                  pathOptions={{
                    color: isHighlighted || isOrigin ? "#2471a3" : color,
                    fillColor: isHighlighted || isOrigin ? "#3498db" : color,
                    fillOpacity: isOrigin ? 1 : isHighlighted ? 0.95 : 0.82,
                    weight: isOrigin ? 2.5 : 1,
                  }}
                >
                  <Popup minWidth={260} maxWidth={320}>
                    <EnterprisePopup
                      enterprise={enterprise}
                      onDiscover={handleDiscover}
                      discovering={discovering && origin?.enterprise_id === enterprise.enterprise_id}
                    />
                  </Popup>
                </CircleMarker>
              );
            })}

            {symbiosisLinks.map((link) => (
              <Polyline
                key={`sym-${link.targetId}`}
                positions={[link.from, link.to]}
                pathOptions={{
                  color: "#2471a3",
                  weight: 2,
                  opacity: 0.65,
                  dashArray: "6 8",
                }}
              />
            ))}

            {tradeCorridors.map((corridor) => (
              <Polyline
                key={`trade-${corridor.id}`}
                positions={corridor.positions}
                pathOptions={{
                  color: "#27ae60",
                  weight: 3,
                  opacity: 0.85,
                  dashArray: "10 10",
                  className: "trade-corridor-line",
                }}
              />
            ))}
          </MapContainer>
        </div>

        <aside className="map-legend panel">
          <h3>Sector legend</h3>
          <ul className="map-legend__list">
            {Object.entries(SECTOR_COLORS).map(([sector, color]) => (
              <li key={sector}>
                <span className="map-legend__dot" style={{ background: color }} />
                <span>
                  <strong>{SECTOR_LABELS[sector] ?? sector}</strong>
                  <small>{sector}</small>
                </span>
              </li>
            ))}
          </ul>
          <div className="map-legend__note">
            <p>
              <strong style={{ color: "#27ae60" }}>Green dashed lines</strong> — active
              agreed trades from your account
            </p>
            <p>
              <strong style={{ color: "#2471a3" }}>Blue dashed lines</strong> — compatible
              buyers discovered within 150 km
            </p>
          </div>
          {origin && (
            <div className="map-legend__selection">
              <small>Selected origin</small>
              <strong>{origin.name}</strong>
              <span>
                {highlightedIds.size} compatible enterprises within 150 km
              </span>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
