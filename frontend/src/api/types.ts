// Mirrors backend/contracts/openapi.json exactly. Do not rename fields here
// without a corresponding contract change from A (see docs/INTEGRATION_CHECKLIST.md).
// Units: money = integer paise, quantity = integer kg, distance = integer meters.

export type Window = { start: string; end: string };

export type Location = {
  district: string;
  lat: number | null;
  lon: number | null;
  precision: "district" | "confirmed_site";
};

export type Role = "buyer" | "seller";

export type Business = {
  id: string;
  name: string;
  enterprise_id: string | null;
  roles: Role[];
  receiving_processes: string[];
  location: Location;
};

export type ListingStatus = "open" | "closed";

export type Listing = {
  id: string;
  seller: Business;
  material_id: string;
  available_quantity_kg: number;
  asking_price_paise_per_tonne: number;
  moisture_pct: number;
  contamination_notes: string;
  pickup_window: Window;
  location: Location;
  status: ListingStatus;
};

export type OwnListing = Listing & { seller_floor_paise_per_tonne: number };

export type RequirementStatus = "open" | "fulfilled" | "closed";

export type Requirement = {
  id: string;
  buyer: Business;
  material_id: string;
  receiving_process_id: string;
  quantity_kg: number;
  max_moisture_pct: number;
  delivery_window: Window;
  location: Location;
  status: RequirementStatus;
};

export type OwnRequirement = Requirement & { buyer_max_total_paise: number };

export type TransportOption = {
  id: string;
  listing_id: string;
  requirement_id: string;
  label: string;
  freight_paise: number;
  capacity_kg: number;
  pickup_at: string;
  delivery_at: string;
  expires_at: string;
  source: "entered_quote" | "configured_estimate";
  distance_m: number | null;
  distance_basis: "road" | "district_straight_line" | "unknown";
};

export type Costs = {
  material_paise: number;
  freight_paise: number;
  buyer_total_paise: number;
  seller_receives_paise: number;
};

export type ReasonCode =
  | "MATERIAL_MISMATCH"
  | "PROCESS_UNCONFIRMED"
  | "QUALITY_MISMATCH"
  | "QUALITY_REVIEW_REQUIRED"
  | "INSUFFICIENT_QUANTITY"
  | "TIME_WINDOW_MISMATCH"
  | "NO_TRANSPORT_OPTION";

export type MatchCandidate = {
  listing: Listing;
  pathway_use: string;
  transport_options: TransportOption[];
  initial_best_cost: Costs;
};

export type MatchesResponse = {
  requirement_id: string;
  candidates: MatchCandidate[];
  excluded: { listing_id: string; reason_codes: ReasonCode[] }[];
  missing_transport_listing_ids: string[];
};

export type NegotiationStatus = "queued" | "running" | "agreed" | "no_deal" | "failed";

export type OfferAuthor = "buyer" | "seller" | "broker";
export type OfferAction = "propose" | "counter" | "accept" | "reject";

export type Offer = {
  id: string;
  listing_id: string;
  transport_option_id: string;
  quantity_kg: number;
  unit_price_paise_per_tonne: number;
  costs: Costs;
  pickup_at: string;
  delivery_at: string;
  author: OfferAuthor;
  action: OfferAction;
  responds_to_offer_id: string | null;
  explanation: string;
  expires_at: string;
};

export type FailureCode =
  | "BUDGET_NOT_MET"
  | "SELLER_DECLINED"
  | "QUOTE_EXPIRED"
  | "STALE_STOCK"
  | "ROUND_LIMIT"
  | "PROVIDER_UNAVAILABLE"
  | "INVALID_MODEL_OUTPUT"
  | "INTERRUPTED";

export type Negotiation = {
  id: string;
  requirement_id: string;
  status: NegotiationStatus;
  round: number;
  max_rounds: number;
  current_listing_id: string | null;
  failure_code: FailureCode | null;
  deal_id: string | null;
  offers: Offer[];
  created_at: string;
  updated_at: string;
};

export type EventType =
  | "started"
  | "offer"
  | "candidate_rejected"
  | "agreed"
  | "no_deal"
  | "failed";

export type Event = {
  seq: number;
  type: EventType;
  actor: "buyer" | "seller" | "broker" | "system";
  message: string;
  offer_id: string | null;
  created_at: string;
};

export type DealStatus = "agreed" | "pickup_scheduled" | "collected" | "delivered" | "cancelled";

export type Deal = {
  id: string;
  negotiation_id: string;
  requirement_id: string;
  listing_id: string;
  seller: Business;
  buyer: Business;
  material_id: string;
  intended_use: string;
  quantity_kg: number;
  unit_price_paise_per_tonne: number;
  costs: Costs;
  transport_option: TransportOption;
  status: DealStatus;
  created_at: string;
};

export type Paginated<T> = { items: T[]; next_cursor: string | null };

export type ApiError = { error: { code: string; message: string; details: Record<string, unknown> } };

export type ReferenceData = {
  materials: { id: string; name: string }[];
  districts: { name: string; lat: number; lon: number }[];
  receiving_processes: { id: string; name: string; material_ids: string[] }[];
};

// Request payload shapes (fields the client sends, excluding server-assigned ones)

export type CreateListingInput = Omit<Listing, "id" | "seller" | "status"> & {
  seller_floor_paise_per_tonne: number;
};

export type UpdateListingInput = Partial<
  Pick<Listing, "asking_price_paise_per_tonne" | "pickup_window" | "status"> & {
    seller_floor_paise_per_tonne: number;
  }
>;

export type CreateRequirementInput = Omit<Requirement, "id" | "buyer" | "status"> & {
  buyer_max_total_paise: number;
};

export type CreateTransportOptionInput = Omit<TransportOption, "id">;

export type StartNegotiationInput = { requirement_id: string; listing_ids: string[] };

export type NegotiationSummary = {
  id: string;
  requirement_id: string;
  status: NegotiationStatus;
  created_at: string;
  deal_id: string | null;
};
