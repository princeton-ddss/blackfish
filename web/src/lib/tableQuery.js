// GitHub-issues-style query parsing + matching for client-side table filtering.
//
// A query string mixes free text with `key:value` qualifiers, e.g.
//   status:failed file:whisper report
// parses to bare text ["report"] plus a qualifier {status: ["failed"], file:
// ["whisper"]}. Repeating a key ORs its values (`status:failed status:success`).
// Quoting a value preserves spaces: `name:"my job"`.

/**
 * Parse a raw query string into bare text terms and keyed qualifiers.
 * @param {string} raw
 * @returns {{ text: string[], filters: Record<string, string[]> }}
 */
export function parseQuery(raw) {
  const text = [];
  const filters = {};
  if (!raw) return { text, filters };

  // Tokenize on whitespace, but keep quoted spans (single- or double-quoted)
  // together so `name:"my job"` is one token.
  const tokens = raw.match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) || [];

  for (const token of tokens) {
    const sep = token.indexOf(":");
    // A leading ':' or no ':' means it's free text, not a qualifier.
    if (sep > 0) {
      const key = token.slice(0, sep).toLowerCase();
      const value = unquote(token.slice(sep + 1));
      if (value !== "") {
        (filters[key] ??= []).push(value.toLowerCase());
        continue;
      }
    }
    const bare = unquote(token);
    if (bare !== "") text.push(bare.toLowerCase());
  }

  return { text, filters };
}

function unquote(s) {
  if (
    s.length >= 2 &&
    ((s[0] === '"' && s[s.length - 1] === '"') ||
      (s[0] === "'" && s[s.length - 1] === "'"))
  ) {
    return s.slice(1, -1);
  }
  return s;
}

/**
 * Filter rows against a parsed query. Filtering is qualifier-only: a token
 * narrows the list only when it is `key:value` with a *known* key and a
 * non-empty value. Bare text, a partial key (no `:` yet), `key:` with no value,
 * and unknown keys are all ignored rather than treated as failed matches — so a
 * query that has nothing actionable yet (still being typed) returns all rows
 * instead of a premature empty result.
 *
 * @param {Array<object>} rows
 * @param {string} raw - the raw query string
 * @param {object} config
 * @param {Record<string, (row: object) => string|null>} config.fields - maps a
 *   qualifier key to a function returning the row's comparable string. Values
 *   match as case-insensitive substrings.
 * @returns {Array<object>}
 */
export function applyQuery(rows, raw, { fields = {} } = {}) {
  const { filters } = parseQuery(raw);

  // Keep only qualifiers whose key is known; unknown/partial keys are ignored.
  const active = Object.entries(filters).filter(([key]) => fields[key]);
  if (active.length === 0) return rows;

  return rows.filter((row) => {
    // Every active qualifier key must match (AND across keys); within a key,
    // any of its values matches (OR).
    for (const [key, values] of active) {
      const rowVal = fields[key](row);
      const rowStr = rowVal == null ? "" : String(rowVal).toLowerCase();
      if (!values.some((v) => rowStr.includes(v))) return false;
    }

    return true;
  });
}

/**
 * Return a new query string with `key` set to exactly `value` (replacing any
 * existing values for that key), or with `key` removed when `value` is null/"".
 * Bare text and other qualifiers are preserved in their original order. Used by
 * dropdown facets that edit the canonical query string.
 *
 * @param {string} raw
 * @param {string} key
 * @param {string|null} value
 * @returns {string}
 */
export function setQueryFilter(raw, key, value) {
  return setQueryFilters(raw, key, value == null || value === "" ? [] : [value]);
}

/**
 * Return a new query string with `key` set to exactly `values` (replacing all
 * existing values for that key). An empty array removes the key entirely. Bare
 * text and other qualifiers are preserved in their original order.
 *
 * @param {string} raw
 * @param {string} key
 * @param {string[]} values
 * @returns {string}
 */
export function setQueryFilters(raw, key, values) {
  const tokens = (raw || "").match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) || [];
  const kept = tokens.filter((t) => {
    const sep = t.indexOf(":");
    if (sep <= 0) return true;
    return t.slice(0, sep).toLowerCase() !== key.toLowerCase();
  });
  for (const value of values) {
    if (value == null || value === "") continue;
    const needsQuote = /\s/.test(value);
    kept.push(`${key}:${needsQuote ? `"${value}"` : value}`);
  }
  return kept.join(" ");
}

/**
 * Add or remove a single value for `key`, preserving that key's other values.
 * Used by multi-select dropdowns to toggle one checkbox.
 *
 * @param {string} raw
 * @param {string} key
 * @param {string} value
 * @returns {string}
 */
export function toggleQueryFilter(raw, key, value) {
  const v = value.toLowerCase();
  const current = getQueryFilters(raw, key);
  const next = current.includes(v)
    ? current.filter((x) => x !== v)
    : [...current, v];
  return setQueryFilters(raw, key, next);
}

/**
 * Read the (single) current value of a qualifier key from a raw query, or null
 * if unset. Lets a single-select dropdown reflect the canonical query string.
 * @param {string} raw
 * @param {string} key
 * @returns {string|null}
 */
export function getQueryFilter(raw, key) {
  const values = getQueryFilters(raw, key);
  return values.length > 0 ? values[0] : null;
}

/**
 * Read all values of a qualifier key from a raw query (empty if unset). Lets a
 * multi-select dropdown reflect the canonical query string.
 * @param {string} raw
 * @param {string} key
 * @returns {string[]}
 */
export function getQueryFilters(raw, key) {
  const { filters } = parseQuery(raw);
  return filters[key.toLowerCase()] ?? [];
}
