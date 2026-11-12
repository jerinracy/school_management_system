import fs from "node:fs";
import path from "node:path";

const localesDir = path.resolve(import.meta.dirname, "../src/i18n/locales");
const en = JSON.parse(fs.readFileSync(path.join(localesDir, "en.json"), "utf8"));
const bn = JSON.parse(fs.readFileSync(path.join(localesDir, "bn.json"), "utf8"));

function flattenKeys(obj, prefix = "") {
  return Object.entries(obj).flatMap(([key, value]) => {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return flattenKeys(value, fullKey);
    }
    return [fullKey];
  });
}

const enKeys = new Set(flattenKeys(en));
const bnKeys = new Set(flattenKeys(bn));

const missingInBn = [...enKeys].filter((k) => !bnKeys.has(k));
const missingInEn = [...bnKeys].filter((k) => !enKeys.has(k));

if (missingInBn.length > 0 || missingInEn.length > 0) {
  if (missingInBn.length > 0) {
    console.error("Missing in bn.json:", missingInBn);
  }
  if (missingInEn.length > 0) {
    console.error("Missing in en.json:", missingInEn);
  }
  process.exit(1);
}

console.log(`i18n parity check passed (${enKeys.size} keys in en.json and bn.json).`);
