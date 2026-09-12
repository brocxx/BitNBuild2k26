// Single import point for every page: `import { api } from "../api"`.
// The active implementation is chosen once, here, based on VITE_API_MODE.

import type { ApiClient } from "./ApiClient";
import { mockClient } from "./mock";
import { realClient } from "./client";

export const API_MODE = import.meta.env.VITE_API_MODE;

export const api: ApiClient = API_MODE === "real" ? realClient : mockClient;

export * from "./types";
export type { ApiClient } from "./ApiClient";
