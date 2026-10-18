import type { RoleCode } from "@aureon/shared-types";

export interface AuthRole {
  id: string;
  code: RoleCode;
  name_i18n_key: string;
  pillar_scope: string[];
  pillar_agg_scope: string[];
  review_pillars: string[];
  can_view_salary: boolean;
  home_route: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  salutation: string | null;
  role: AuthRole;
  is_demo_account: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface LoginResponseData {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUser;
}

export interface SwitchRoleResponseData {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUser;
  home_route: string;
}

export interface DemoUserItem {
  role_code: RoleCode;
  role_name_i18n_key: string;
  full_name: string;
  user_id: string;
}

export interface MeResponseData {
  user: AuthUser;
  permissions: Record<string, unknown>;
  demo_mode: boolean;
}

export interface AuthSession {
  accessToken: string;
  user: AuthUser;
  expiresAt: string;
  homeRoute: string;
}
