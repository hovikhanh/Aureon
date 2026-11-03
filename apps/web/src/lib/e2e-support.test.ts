/**
 * TC-M6-05 (unit) — R-DEC-167: the E2E support runner reads `.env` like the API does and never lets
 * a secret reach a Playwright error. All values below are made-up samples.
 */
import { describe, expect, it } from "vitest";
import { redactSecrets, unquote } from "../../e2e/support/seed";

describe("unquote (dotenv semantics)", () => {
  it.each([
    [`'{"a": 1}'`, `{"a": 1}`], // single quotes were kept → json.loads failed at char 0
    [`"x y"`, "x y"],
    ["plain", "plain"],
    [`'mismatch"`, `'mismatch"`],
    ["''", ""],
  ])("%s", (raw, out) => expect(unquote(raw)).toBe(out));
});

describe("redactSecrets", () => {
  const sample = "Sample-Pa55word!";
  it("masks a pydantic settings dump, secret-named pairs and URL credentials", () => {
    const text = [
      `Value error, Expecting value [type=value_error, input_value={'database_url': 'postgre...ssword': '${sample}'}, input_type=dict]`,
      `'demo_admin_password': '${sample}'`,
      `DEMO_ADMIN_PASSWORD=${sample}`,
      `OMNIROUTE_API_KEY="${sample}"`,
      `connect postgresql+psycopg://aureon:${sample}@localhost:5432/aureon`,
      "status=FAILED reason=EXTRACTION_FAILED", // non-secret text stays readable
    ].join("\n");
    const out = redactSecrets(text);
    expect(out).not.toContain(sample);
    expect(out).toContain("status=FAILED reason=EXTRACTION_FAILED");
    expect(out).toContain("input_value=<redacted>");
  });
});
