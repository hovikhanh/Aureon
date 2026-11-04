/** Server-side display capabilities of the records pages (the API enforces — R-DEC-161/M7). */
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { canDomain } from "@/lib/permissions";
import type { RecordCaps } from "./RecordCrud";
import type { Domain } from "./specs";

export async function recordCaps(domain: Domain): Promise<RecordCaps> {
  const u = (await getServerSession(authOptions))?.user;
  const perms = u?.permissions ?? [];
  const pillars = u?.scopePillars ?? [];
  const role = u?.role ?? "";
  // `/hr/departments`, `/hr/employees` are khối-O records; EMP / REV have no structure scope (10 §7.2.1)
  const hrReader = canDomain(perms, pillars, "hr") && role !== "EMP" && role !== "REV";
  return {
    userId: u?.id ?? "",
    role,
    scopePillars: pillars,
    departmentId: u?.departmentId ?? null,
    permissions: perms,
    canWrite: canDomain(perms, pillars, domain, "write"),
    canReadDepartments: hrReader,
    canReadClients: canDomain(perms, pillars, "sales"),
    canReadEmployees: hrReader,
    canPickUser: perms.includes("platform:read"),
  };
}
