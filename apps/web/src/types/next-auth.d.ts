import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    permissions: string[];
    accessToken: string;
    refreshToken: string;
    expiresAt: number;
  }
  interface Session {
    user: { id: string; email: string; name: string; role: string; permissions: string[] };
    error?: "RefreshFailed";
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    uid: string;
    role: string;
    permissions: string[];
    accessToken: string;
    refreshToken: string;
    expiresAt: number;
    error?: "RefreshFailed";
  }
}
