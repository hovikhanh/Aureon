import { apiFetch } from "@/lib/api-client";
import type { RoleCode } from "@aureon/shared-types";
import type {
  DemoUserItem,
  LoginResponseData,
  MeResponseData,
  SwitchRoleResponseData,
} from "./types";

/**
 * EP-02 POST /api/v1/auth/login (10 EP-02).
 */
export async function loginApi(email: string, password: string): Promise<LoginResponseData> {
  const envelope = await apiFetch<LoginResponseData>("auth/login", {
    method: "POST",
    json: { email, password },
  });
  return envelope.data;
}

/**
 * EP-03 GET /api/v1/auth/me (10 EP-03).
 */
export async function getMeApi(token: string): Promise<MeResponseData> {
  const envelope = await apiFetch<MeResponseData>("auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return envelope.data;
}

/**
 * EP-04 POST /api/v1/auth/switch-role (10 EP-04).
 */
export async function switchRoleApi(
  targetRoleCode: RoleCode,
  token: string,
): Promise<SwitchRoleResponseData> {
  const envelope = await apiFetch<SwitchRoleResponseData>("auth/switch-role", {
    method: "POST",
    json: { target_role_code: targetRoleCode },
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return envelope.data;
}

/**
 * EP-05 GET /api/v1/auth/demo-users (10 EP-05).
 */
export async function getDemoUsersApi(token: string): Promise<DemoUserItem[]> {
  const envelope = await apiFetch<DemoUserItem[]>("auth/demo-users", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return envelope.data;
}
