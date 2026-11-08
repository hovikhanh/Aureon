/** Last-resort display of a machine key (`seller_name` → `Seller name`) so `snake_case` never reaches a label. */
export function humanizeKey(key: string): string {
  const words = key.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_\-.]+/g, " ").trim().toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

type T = { (key: string): string; has: (key: string) => boolean };

/** i18n label of an API enum / code under `namespace`, humanised when the catalog has no entry yet. */
export function codeLabel(t: T, namespace: string, code: string): string {
  const key = `${namespace}.${code}`;
  return t.has(key) ? t(key) : humanizeKey(code);
}
