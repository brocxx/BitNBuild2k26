// The single interface mock.ts and client.ts both implement.
// Every page imports the client through ./index, never mock.ts or client.ts directly.

import type {
  Business,
  CreateListingInput,
  CreateRequirementInput,
  CreateTransportOptionInput,
  Deal,
  Event,
  Listing,
  MatchesResponse,
  Negotiation,
  NegotiationSummary,
  OwnListing,
  OwnRequirement,
  Paginated,
  ReferenceData,
  Requirement,
  StartNegotiationInput,
  TransportOption,
  UpdateListingInput,
  DealStatus,
  GreenCertificate,
  MapEnterprisesResponse,
  SymbiosisResult,
} from "./types";

export interface ListListingsParams {
  material_id?: string;
  district?: string;
  cursor?: string | null;
  limit?: number;
}

export interface ApiClient {
  getMe(): Promise<{ user_id: string; business: Business }>;
  getReference(): Promise<ReferenceData>;

  listListings(params?: ListListingsParams): Promise<Paginated<Listing>>;
  getListing(id: string): Promise<Listing>;
  listMyListings(cursor?: string | null): Promise<Paginated<OwnListing>>;
  createListing(input: CreateListingInput): Promise<OwnListing>;
  updateListing(id: string, input: UpdateListingInput): Promise<OwnListing>;

  listMyRequirements(cursor?: string | null): Promise<Paginated<OwnRequirement>>;
  createRequirement(input: CreateRequirementInput): Promise<OwnRequirement>;
  getRequirement(id: string): Promise<OwnRequirement>;
  getMatches(requirementId: string): Promise<MatchesResponse>;

  createTransportOption(input: CreateTransportOptionInput): Promise<TransportOption>;

  startNegotiation(input: StartNegotiationInput, idempotencyKey: string): Promise<{ id: string; status: "queued" }>;
  listMyNegotiations(cursor?: string | null): Promise<Paginated<NegotiationSummary>>;
  getNegotiation(id: string): Promise<Negotiation>;
  getNegotiationEvents(id: string, afterSeq: number): Promise<{ items: Event[]; last_seq: number }>;

  listMyDeals(cursor?: string | null): Promise<Paginated<Deal>>;
  getDeal(id: string): Promise<Deal>;
  updateDealStatus(id: string, status: DealStatus): Promise<Deal>;
  getDealCertificate(id: string): Promise<GreenCertificate>;

  getMapEnterprises(): Promise<MapEnterprisesResponse>;
  getSymbiosisNeighbors(district: string, radiusKm?: number): Promise<SymbiosisResult>;
}
