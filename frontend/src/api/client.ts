// Real mode: talks to A's FastAPI backend. Never embeds Gemini/Supabase
// service keys — only the access token, attached per request.

import type { ApiClient, ListListingsParams } from "./ApiClient";
import type {
  ApiError,
  CreateListingInput,
  CreateRequirementInput,
  CreateTransportOptionInput,
  DealStatus,
  StartNegotiationInput,
  UpdateListingInput,
} from "./types";
import { getAccessToken } from "../auth/supabase";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

class ApiRequestError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;
  constructor(status: number, body: ApiError) {
    super(body.error.message);
    this.code = body.error.code;
    this.status = status;
    this.details = body.error.details;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { idempotencyKey?: string } = {}
): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let body: ApiError;
    try {
      body = await res.json();
    } catch {
      body = { error: { code: "UNKNOWN", message: `Request failed (${res.status})`, details: {} } };
    }
    throw new ApiRequestError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function query(params: Record<string, string | number | null | undefined>): string {
  const usable = Object.entries(params).filter(([, v]) => v !== undefined && v !== null);
  if (!usable.length) return "";
  return "?" + new URLSearchParams(usable.map(([k, v]) => [k, String(v)])).toString();
}

const NIC_BYPRODUCTS: Record<number, string[]> = {
  10: ["rice_husk", "rice_bran"],
  13: ["fabric_cutting_waste", "silk_noil_reeling_waste"],
  16: ["sawdust", "wood_bark", "wood_offcuts"],
  23: ["broken_rejected_bricks_grog", "kiln_fly_ash"],
  25: ["sheet_metal_scrap", "machining_swarf", "mill_scale"],
};

export const realClient: ApiClient = {
  getMe: () => request("/me"),
  getReference: () => request("/reference"),

  listListings: (params?: ListListingsParams) =>
    request(`/listings${query({ ...params })}`),
  getListing: (id) => request(`/listings/${id}`),
  listMyListings: (cursor) => request(`/me/listings${query({ cursor })}`),
  createListing: (input: CreateListingInput) =>
    request("/listings", { method: "POST", body: JSON.stringify(input) }),
  updateListing: (id, input: UpdateListingInput) =>
    request(`/listings/${id}`, { method: "PATCH", body: JSON.stringify(input) }),

  listMyRequirements: (cursor) => request(`/me/requirements${query({ cursor })}`),
  createRequirement: (input: CreateRequirementInput) =>
    request("/requirements", { method: "POST", body: JSON.stringify(input) }),
  getRequirement: (id) => request(`/requirements/${id}`),
  getMatches: (requirementId) => request(`/requirements/${requirementId}/matches`),

  createTransportOption: (input: CreateTransportOptionInput) =>
    request("/transport-options", { method: "POST", body: JSON.stringify(input) }),

  startNegotiation: (input: StartNegotiationInput, idempotencyKey: string) =>
    request("/negotiations", { method: "POST", body: JSON.stringify(input), idempotencyKey }),
  listMyNegotiations: (cursor) => request(`/me/negotiations${query({ cursor })}`),
  getNegotiation: (id) => request(`/negotiations/${id}`),
  getNegotiationEvents: (id, afterSeq) =>
    request(`/negotiations/${id}/events${query({ after_seq: afterSeq })}`),

  listMyDeals: (cursor) => request(`/me/deals${query({ cursor })}`),
  getDeal: (id) => request(`/deals/${id}`),
  updateDealStatus: (id, status: DealStatus) =>
    request(`/deals/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  getDealCertificate: (id) => request(`/deals/${id}/certificate`),


  getMapEnterprises: async () => {
    const res = await request<{ items?: any[]; enterprises?: any[] }>("/map/enterprises?limit=8000");
    const rawList = res.enterprises ?? res.items ?? [];
    return {
      enterprises: rawList.map((item) => ({
        enterprise_id: item.enterprise_id,
        name: item.enterprise_name || item.name || `Enterprise ${item.enterprise_id}`,
        district: item.district,
        lat: item.lat,
        lon: item.lon,
        sector: item.sector || `NIC ${item.nic2_division}`,
        byproducts: item.byproducts || NIC_BYPRODUCTS[item.nic2_division] || [],
      })),
    };
  },

  getSymbiosisNeighbors: async (district: string, radiusKm = 150) => {
    const res = await request<{
      origin?: any;
      query_district?: string;
      radius_km?: number;
      compatible_enterprises?: any[];
      matches?: any[];
    }>(`/map/symbiosis${query({ district, radius_km: radiusKm, limit: 100 })}`);

    if (res.compatible_enterprises) {
      return res as any;
    }

    const matches = res.matches ?? [];
    return {
      origin: res.origin || { district, lat: 14.4644, lon: 75.9218 },
      radius_km: radiusKm,
      compatible_enterprises: matches.map((m) => {
        const ent = m.enterprise;
        return {
          enterprise_id: ent.enterprise_id,
          name: ent.enterprise_name || ent.name,
          district: ent.district,
          lat: ent.lat,
          lon: ent.lon,
          sector: ent.sector || `NIC ${ent.nic2_division}`,
          byproducts: [m.byproduct_name],
        };
      }),
    };
  },
};


export { ApiRequestError };
