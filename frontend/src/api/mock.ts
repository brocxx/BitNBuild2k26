// Mock mode: fully in-memory, no network calls. Lets every screen be built
// and demoed before the backend, Supabase, or Gemini exist.
// Visibly labeled in the UI via <MockModeBanner /> — local development only.

import type { ApiClient, ListListingsParams } from "./ApiClient";
import type {
  Business,
  CreateListingInput,
  CreateRequirementInput,
  CreateTransportOptionInput,
  Deal,
  DealStatus,
  Event,
  Listing,
  MatchesResponse,
  Negotiation,
  NegotiationSummary,
  Offer,
  OwnListing,
  OwnRequirement,
  Paginated,
  ReferenceData,
  StartNegotiationInput,
  TransportOption,
  UpdateListingInput,
} from "./types";
import { DATASET_MATERIALS, DATASET_PATHWAYS } from "../data/datasetReference";
import mapData from "../data/mapEnterprises.json";
import { findCompatibleByDistrict } from "../utils/mapUtils";
import type { MapEnterprise } from "./types";

const now = () => new Date().toISOString();
const inHours = (h: number) => new Date(Date.now() + h * 3600_000).toISOString();
const uid = (prefix: string) => `${prefix}_${Math.random().toString(36).slice(2, 9)}`;

const ME: Business = {
  id: "biz_demo_buyer",
  name: "Enterprise KA-ENT-000783",
  enterprise_id: "KA-ENT-000783",
  roles: ["buyer", "seller"],
  receiving_processes: DATASET_PATHWAYS.map((p) => p.process_id),
  location: { district: "BENGALURU (URBAN)", lat: 12.9716, lon: 77.5946, precision: "district" },
};

const SELLER_KOLAR: Business = {
  id: "biz_seller_kolar",
  name: "Enterprise KA-ENT-000020",
  enterprise_id: "KA-ENT-000020",
  roles: ["seller"],
  receiving_processes: [],
  location: { district: "KOLAR", lat: 13.1359, lon: 78.1294, precision: "district" },
};

const SELLER_BLR_RURAL: Business = {
  id: "biz_seller_blr_rural",
  name: "Enterprise KA-ENT-001312",
  enterprise_id: "KA-ENT-001312",
  roles: ["seller"],
  receiving_processes: [],
  location: { district: "BENGALURU (RURAL)", lat: 13.2847, lon: 77.5375, precision: "district" },
};

const SELLER_BLR_URBAN: Business = {
  id: "biz_seller_blr_urban",
  name: "Enterprise KA-ENT-000089",
  enterprise_id: "KA-ENT-000089",
  roles: ["seller"],
  receiving_processes: [],
  location: { district: "BENGALURU (URBAN)", lat: 12.9716, lon: 77.5946, precision: "district" },
};

const REFERENCE: ReferenceData = {
  materials: DATASET_MATERIALS,
  districts: [
    { name: "KOLAR", lat: 13.1359, lon: 78.1294 },
    { name: "BENGALURU (RURAL)", lat: 13.2847, lon: 77.5375 },
    { name: "BENGALURU (URBAN)", lat: 12.9716, lon: 77.5946 },
    { name: "MANDYA", lat: 12.5223, lon: 76.8975 },
  ],
  receiving_processes: DATASET_PATHWAYS.map((p) => ({
    id: p.process_id,
    name: p.receiver_industry,
    material_ids: [p.material_id],
  })),
};

// Commercial values below are DEMO INPUTS, not dataset prices. The real UI asks
// seller/buyer users for these values. Dataset-derived values are limited to
// enterprise ids, sectors, pathway support, district coordinates and distances.
let listings: OwnListing[] = [
  {
    id: "lst_001",
    seller: SELLER_KOLAR,
    material_id: "rice_husk",
    available_quantity_kg: 2800,
    asking_price_paise_per_tonne: 285000,
    seller_floor_paise_per_tonne: 240000,
    moisture_pct: 11,
    contamination_notes: "Demo seller input: sieved; trace paddy dust.",
    pickup_window: { start: inHours(24), end: inHours(96) },
    location: SELLER_KOLAR.location,
    status: "open",
    negotiation_strategy: "conceder",
  },
  {
    id: "lst_002",
    seller: SELLER_BLR_RURAL,
    material_id: "rice_husk",
    available_quantity_kg: 5000,
    asking_price_paise_per_tonne: 270000,
    seller_floor_paise_per_tonne: 230000,
    moisture_pct: 12,
    contamination_notes: "Demo seller input: no contamination reported.",
    pickup_window: { start: inHours(18), end: inHours(84) },
    location: SELLER_BLR_RURAL.location,
    status: "open",
    negotiation_strategy: "conceder",
  },
  {
    id: "lst_003",
    seller: SELLER_BLR_URBAN,
    material_id: "rice_husk",
    available_quantity_kg: 3400,
    asking_price_paise_per_tonne: 260000,
    seller_floor_paise_per_tonne: 225000,
    moisture_pct: 13,
    contamination_notes: "Demo seller input: quality confirmation required before bulk delivery.",
    pickup_window: { start: inHours(12), end: inHours(72) },
    location: SELLER_BLR_URBAN.location,
    status: "open",
    negotiation_strategy: "conceder",
  },
];

let requirements: OwnRequirement[] = [];

let transportOptions: TransportOption[] = [
  {
    id: "trn_001", listing_id: "lst_001", requirement_id: "req_001",
    label: "Configured freight estimate", freight_paise: 61000,
    capacity_kg: 4000, pickup_at: inHours(30), delivery_at: inHours(36), expires_at: inHours(96),
    source: "configured_estimate", distance_m: 60740, distance_basis: "district_straight_line",
  },
  {
    id: "trn_002", listing_id: "lst_002", requirement_id: "req_001",
    label: "Configured freight estimate", freight_paise: 52000,
    capacity_kg: 4000, pickup_at: inHours(24), delivery_at: inHours(36), expires_at: inHours(84),
    source: "configured_estimate", distance_m: 28000, distance_basis: "district_straight_line",
  },
  {
    id: "trn_003", listing_id: "lst_003", requirement_id: "req_001",
    label: "Configured freight estimate", freight_paise: 30000,
    capacity_kg: 4000, pickup_at: inHours(20), delivery_at: inHours(34), expires_at: inHours(72),
    source: "configured_estimate", distance_m: 0, distance_basis: "district_straight_line",
  },
];

let negotiations: Record<string, Negotiation> = {};
let eventsByNegotiation: Record<string, Event[]> = {};
let deals: Record<string, Deal> = {};
let idempotencyStore: Record<string, { id: string; status: "queued" }> = {};

const MAP_ENTERPRISES = mapData.enterprises as MapEnterprise[];

function calcCosts(unitPricePaisePerTonne: number, quantityKg: number, freightPaise: number) {
  const material_paise = Math.round((unitPricePaisePerTonne * quantityKg) / 1000);
  return {
    material_paise,
    freight_paise: freightPaise,
    buyer_total_paise: material_paise + freightPaise,
    seller_receives_paise: material_paise,
  };
}

function paginate<T>(items: T[]): Paginated<T> {
  return { items, next_cursor: null };
}

deals.deal_demo_corridor = {
  id: "deal_demo_corridor",
  negotiation_id: "neg_demo",
  requirement_id: "req_demo",
  listing_id: "lst_001",
  seller: SELLER_KOLAR,
  buyer: ME,
  material_id: "rice_husk",
  intended_use: "brick_kiln_fuel",
  quantity_kg: 2800,
  unit_price_paise_per_tonne: 260000,
  costs: calcCosts(260000, 2800, 61000),
  transport_option: transportOptions[0],
  status: "agreed",
  created_at: now(),
};

// Simulates the buyer/seller/broker negotiation with a couple of scripted
// rounds so the polling UI has real state transitions to render.
function runMockNegotiation(negId: string, requirementId: string, listingId: string) {
  const requirement = requirements.find((r) => r.id === requirementId)!;
  const listing = listings.find((l) => l.id === listingId)!;
  const transport = transportOptions.find((t) => t.listing_id === listingId && t.requirement_id === requirementId)
    ?? transportOptions.find((t) => t.listing_id === listingId)!;

  const push = (e: Omit<Event, "seq" | "created_at">) => {
    const list = eventsByNegotiation[negId] ?? [];
    list.push({ ...e, seq: list.length + 1, created_at: now() });
    eventsByNegotiation[negId] = list;
  };

  push({ type: "started", actor: "system", message: `Negotiation started with ${listing.seller.name}. Private limits remain hidden.`, offer_id: null });

  const affordableMaterialPaise = Math.max(0, requirement.buyer_max_total_paise - transport.freight_paise);
  const buyerMaxUnit = Math.floor((affordableMaterialPaise * 1000) / requirement.quantity_kg);
  const canDeal = buyerMaxUnit >= listing.seller_floor_paise_per_tonne;
  const settlement = Math.max(
    listing.seller_floor_paise_per_tonne,
    Math.min(Math.round(listing.asking_price_paise_per_tonne * 0.95), buyerMaxUnit)
  );

  const steps = canDeal
    ? [
        { author: "seller" as const, action: "propose" as const, price: listing.asking_price_paise_per_tonne },
        { author: "buyer" as const, action: "counter" as const, price: Math.min(Math.round(listing.asking_price_paise_per_tonne * 0.9), buyerMaxUnit) },
        { author: "seller" as const, action: "counter" as const, price: settlement },
        { author: "broker" as const, action: "accept" as const, price: settlement },
      ]
    : [
        { author: "seller" as const, action: "propose" as const, price: listing.asking_price_paise_per_tonne },
        { author: "buyer" as const, action: "counter" as const, price: buyerMaxUnit },
      ];

  const offers: Offer[] = [];
  let round = 0;
  const timer = setInterval(() => {
    const neg = negotiations[negId];
    if (!neg || neg.status !== "running") { clearInterval(timer); return; }
    if (round >= steps.length) {
      if (!canDeal) {
        neg.status = "no_deal";
        neg.failure_code = "BUDGET_NOT_MET";
        neg.updated_at = now();
        push({ type: "no_deal", actor: "system", message: "No deal: buyer delivered-cost ceiling cannot meet the seller floor plus freight. Try lower freight, a larger batch, or another nearby supplier.", offer_id: offers.length ? offers[offers.length - 1].id : null });
      }
      clearInterval(timer); return;
    }

    const step = steps[round];
    const costs = calcCosts(step.price, requirement.quantity_kg, transport.freight_paise);
    const offer: Offer = {
      id: uid("off"), listing_id: listing.id, transport_option_id: transport.id,
      quantity_kg: requirement.quantity_kg, unit_price_paise_per_tonne: step.price, costs,
      pickup_at: transport.pickup_at, delivery_at: transport.delivery_at,
      author: step.author, action: step.action,
      responds_to_offer_id: offers.length ? offers[offers.length - 1].id : null,
      explanation: step.action === "accept"
        ? "Delivered cost is within the buyer boundary and the seller floor is protected. Agreement reached."
        : `${step.author === "seller" ? "Seller" : "Buyer"} ${step.action === "propose" ? "opened" : "countered"} at ₹${(step.price / 100).toLocaleString("en-IN")}/tonne.`,
      expires_at: inHours(6),
    };
    offers.push(offer); neg.offers = [...offers]; neg.round = round + 1; neg.updated_at = now();
    push({ type: "offer", actor: step.author, message: offer.explanation, offer_id: offer.id });
    round += 1;

    if (step.action === "accept") {
      const dealId = uid("deal");
      deals[dealId] = {
        id: dealId, negotiation_id: negId, requirement_id: requirement.id, listing_id: listing.id,
        seller: listing.seller, buyer: requirement.buyer, material_id: listing.material_id,
        intended_use: requirement.receiving_process_id, quantity_kg: requirement.quantity_kg,
        unit_price_paise_per_tonne: step.price, costs, transport_option: transport,
        status: "agreed", created_at: now(),
      };
      neg.status = "agreed"; neg.deal_id = dealId; listing.available_quantity_kg -= requirement.quantity_kg;
      requirement.status = "fulfilled";
      push({ type: "agreed", actor: "system", message: "Agreement reached and stock reserved.", offer_id: offer.id });
      clearInterval(timer);
    }
  }, 1100);
}

export const mockClient: ApiClient = {
  async getMe() {
    return { user_id: "user_demo", business: ME };
  },
  async getReference() {
    return REFERENCE;
  },

  async listListings(params?: ListListingsParams) {
    let items = listings.filter((l) => l.status === "open");
    if (params?.material_id) items = items.filter((l) => l.material_id === params.material_id);
    if (params?.district) items = items.filter((l) => l.location.district === params.district);
    return paginate(items);
  },
  async getListing(id: string) {
    const found = listings.find((l) => l.id === id);
    if (!found) throw new Error("Listing not found");
    return found;
  },
  async listMyListings() {
    return paginate(listings.filter((l) => l.seller.id === ME.id));
  },
  async createListing(input: CreateListingInput) {
    const created: OwnListing = {
      ...input,
      id: uid("lst"),
      seller: ME,
      status: "open",
      negotiation_strategy: input.negotiation_strategy ?? "conceder",
    };
    listings = [...listings, created];
    return created;
  },
  async updateListing(id: string, input: UpdateListingInput) {
    const idx = listings.findIndex((l) => l.id === id);
    if (idx === -1) throw new Error("Listing not found");
    listings[idx] = { ...listings[idx], ...input };
    return listings[idx];
  },

  async listMyRequirements() {
    return paginate(requirements.filter((r) => r.buyer.id === ME.id));
  },
  async createRequirement(input: CreateRequirementInput) {
    const created: OwnRequirement = {
      ...input,
      id: uid("req"),
      buyer: ME,
      status: "open",
      negotiation_strategy: input.negotiation_strategy ?? "conceder",
    };
    requirements = [...requirements, created];
    return created;
  },
  async getRequirement(id: string) {
    const found = requirements.find((r) => r.id === id);
    if (!found) throw new Error("Requirement not found");
    return found;
  },
  async getMatches(requirementId: string) {
    const requirement = requirements.find((r) => r.id === requirementId);
    if (!requirement) throw new Error("Requirement not found");
    const eligible = listings
      .filter((l) => l.status === "open" && l.material_id === requirement.material_id)
      .filter((l) => l.available_quantity_kg >= requirement.quantity_kg && l.moisture_pct <= requirement.max_moisture_pct)
      .sort((a, b) => {
        const da = transportOptions.find((t) => t.listing_id === a.id)?.distance_m ?? Number.MAX_SAFE_INTEGER;
        const db = transportOptions.find((t) => t.listing_id === b.id)?.distance_m ?? Number.MAX_SAFE_INTEGER;
        return da - db; // nearby compatible supplier preference
      });
    const response: MatchesResponse = {
      requirement_id: requirementId,
      candidates: eligible.map((listing) => {
        const transport = transportOptions.filter((t) => t.listing_id === listing.id);
        const best = transport[0];
        return {
          listing,
          pathway_use: requirement.receiving_process_id,
          transport_options: transport,
          initial_best_cost: best
            ? calcCosts(listing.asking_price_paise_per_tonne, requirement.quantity_kg, best.freight_paise)
            : calcCosts(listing.asking_price_paise_per_tonne, requirement.quantity_kg, 0),
        };
      }),
      excluded: [],
      missing_transport_listing_ids: eligible
        .filter((l) => !transportOptions.some((t) => t.listing_id === l.id))
        .map((l) => l.id),
    };
    return response;
  },

  async createTransportOption(input: CreateTransportOptionInput) {
    const created: TransportOption = { ...input, id: uid("trn") };
    transportOptions = [...transportOptions, created];
    return created;
  },

  async startNegotiation(input: StartNegotiationInput, idempotencyKey: string) {
    if (idempotencyStore[idempotencyKey]) return idempotencyStore[idempotencyKey];
    const negId = uid("neg");
    const listingId = input.listing_ids[0];
    const negotiation: Negotiation = {
      id: negId,
      requirement_id: input.requirement_id,
      status: "running",
      round: 0,
      max_rounds: 4,
      current_listing_id: listingId,
      failure_code: null,
      deal_id: null,
      offers: [],
      created_at: now(),
      updated_at: now(),
    };
    negotiations[negId] = negotiation;
    eventsByNegotiation[negId] = [];
    runMockNegotiation(negId, input.requirement_id, listingId);
    const result = { id: negId, status: "queued" as const };
    idempotencyStore[idempotencyKey] = result;
    return result;
  },
  async listMyNegotiations() {
    const list: NegotiationSummary[] = Object.values(negotiations).map((n) => ({
      id: n.id,
      requirement_id: n.requirement_id,
      status: n.status,
      created_at: n.created_at,
      deal_id: n.deal_id,
    }));
    return paginate(list);
  },
  async getNegotiation(id: string) {
    const found = negotiations[id];
    if (!found) throw new Error("Negotiation not found");
    return found;
  },
  async getNegotiationEvents(id: string, afterSeq: number) {
    const all = eventsByNegotiation[id] ?? [];
    const items = all.filter((e) => e.seq > afterSeq);
    return { items, last_seq: all.length ? all[all.length - 1].seq : afterSeq };
  },

  async listMyDeals() {
    return paginate(Object.values(deals));
  },
  async getDeal(id: string) {
    const found = deals[id];
    if (!found) throw new Error("Deal not found");
    return found;
  },
  async updateDealStatus(id: string, status: DealStatus) {
    const found = deals[id];
    if (!found) throw new Error("Deal not found");
    found.status = status;
    return found;
  },
  async getDealCertificate(id: string) {
    const found = deals[id];
    if (!found) throw new Error("Deal not found");
    return {
      certificate_id: `CERT-KIB-${found.id.slice(0, 8).toUpperCase()}-2026`,
      issuer: "Karnataka Industrial Byproduct Exchange (KIB) & Circular Economy Authority",
      deal_id: found.id,
      trade_date: found.created_at,
      seller: found.seller,
      buyer: found.buyer,
      material_id: found.material_id,
      material_display_name: found.material_id.replace("_", " ").toUpperCase(),
      quantity_kg: found.quantity_kg,
      transport_distance_km: (found.transport_option.distance_m || 150000) / 1000,
      esg_metrics: {
        material_id: found.material_id,
        material_display_name: found.material_id.replace("_", " "),
        replaces_virgin: "sub-bituminous coal",
        quantity_kg: found.quantity_kg,
        distance_km: (found.transport_option.distance_m || 150000) / 1000,
        gross_co2e_avoided_kg: (found.quantity_kg / 1000) * 1400,
        transport_co2e_kg: (found.quantity_kg / 1000) * ((found.transport_option.distance_m || 150000) / 1000) * 0.062,
        net_co2e_avoided_kg: (found.quantity_kg / 1000) * 1400 - (found.quantity_kg / 1000) * ((found.transport_option.distance_m || 150000) / 1000) * 0.062,
        landfill_diverted_kg: found.quantity_kg,
        carbon_credits_estimated: ((found.quantity_kg / 1000) * 1400) / 1000,
        emission_factor_source: "IPCC 2006 Guidelines Table 2.4",
      },
      verification_hash: "e8fac94d0a2a3a7a2770619ec05afbcf2bdc4721b84c297b112b6937ce9c0fd2",
      methodology: "IPCC 2006 Guidelines for National Greenhouse Gas Inventories & MoRTH India Freight Factor 2022",
    };
  },


  async getMapEnterprises() {
    return { enterprises: MAP_ENTERPRISES };
  },

  async getSymbiosisNeighbors(district: string, radiusKm = 150) {
    const inDistrict = MAP_ENTERPRISES.filter((e) => e.district === district);
    const avgLat =
      inDistrict.reduce((sum, e) => sum + e.lat, 0) / Math.max(inDistrict.length, 1);
    const avgLon =
      inDistrict.reduce((sum, e) => sum + e.lon, 0) / Math.max(inDistrict.length, 1);
    const compatible = findCompatibleByDistrict(district, MAP_ENTERPRISES, radiusKm);
    return {
      origin: { district, lat: avgLat, lon: avgLon },
      radius_km: radiusKm,
      compatible_enterprises: compatible,
    };
  },
};
