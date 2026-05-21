/**
 * Mini App authentication — POSTs initData + workspace_id to the backend,
 * stores the JWT, exposes it for subsequent API calls.
 */
import axios from "axios";

const TOKEN_KEY = "tma_access_token";

export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    telegram_id: number;
    first_name: string;
    last_name: string | null;
    telegram_username: string | null;
  };
  workspace: {
    id: string;
    name: string;
    type: string | null;
  };
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export async function authenticate(
  initData: string,
  workspaceId: string,
): Promise<AuthResponse> {
  const res = await axios.post<AuthResponse>(
    `${API_URL}/api/auth/telegram`,
    { init_data: initData, workspace_id: workspaceId },
    { headers: { "Content-Type": "application/json" } },
  );
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, res.data.access_token);
  }
  return res.data;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

/** Axios instance with automatic Bearer header from stored token. */
export const tmaApi = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { "Content-Type": "application/json" },
});

tmaApi.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401 (expired/revoked JWT) drop the token and reload so the page re-auths
// from fresh Telegram initData. Guard against loops: only reload if we actually
// had a token (i.e. it went stale), not on the very first unauthenticated call.
tmaApi.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401 && getStoredToken()) {
      clearStoredToken();
      if (typeof window !== "undefined") window.location.reload();
    }
    return Promise.reject(error);
  },
);
