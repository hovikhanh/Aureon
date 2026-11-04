import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    permissions: string[];
    /** DIR khối (R-DEC-12a) from the access-token claim; display only — the API enforces. */
    scopePillars: string[];
    departmentId?: string | null;
    accessToken: string;
    refreshToken: string;
    expiresAt: number;
  }
  interface Session {
    user: { id: string; email: string; name: string; role: string; permissions: string[]; scopePillars: string[]; departmentId?: string | null };
    error?: "RefreshFailed";
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    uid: string;
    role: string;
    permissions: string[];
    scopePillars: string[];
    departmentId?: string | null;
    accessToken: string;
    refreshToken: string;
    expiresAt: number;
    error?: "RefreshFailed";
  }
}
