import { useMemo, useState } from "react";
import { applyQuery, getQueryFilters } from "./tableQuery";

// asc -> desc -> off, cycled by repeated clicks on the same header.
const NEXT_DIR = { asc: "desc", desc: null, null: "asc" };

/**
 * Compare two non-null values. Numbers compare numerically; date-like strings
 * by timestamp; else lexically. Null handling lives in the sort itself so that
 * nulls stay last regardless of direction.
 */
function compare(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;

  const da = Date.parse(a);
  const db = Date.parse(b);
  if (!Number.isNaN(da) && !Number.isNaN(db)) return da - db;

  return String(a).localeCompare(String(b));
}

const isNil = (v) => v == null || v === "";

/**
 * Client-side table controls: a canonical query string (free text + key:value
 * qualifiers) and clickable-header sort state, held in memory. Returns the
 * derived rows plus the handlers a table's search bar and headers bind to.
 *
 * @param {Array<object>} rows
 * @param {object} config
 * @param {Record<string, (row: object) => string|null>} config.filterFields -
 *   qualifier key -> accessor (see applyQuery)
 * @param {Record<string, Record<string, (row: object) => boolean>>}
 *   config.predicateFilters - dropdown-backed shortcut groups that express
 *   intent awkward to type as raw qualifiers. Keyed by the query key the
 *   dropdown writes (e.g. `filter`, `progress`), then by option value ->
 *   predicate. One option per group applies at a time (single-select), ANDed
 *   with every other group and with any typed field qualifiers.
 * @param {Record<string, (row: object) => any>} config.sortFields - sort key ->
 *   accessor returning the comparable value for that column
 * @param {{ key: string, dir: "asc"|"desc" }} [config.defaultSort]
 */
export function useTableControls(
  rows,
  {
    filterFields = {},
    predicateFilters = {},
    sortFields = {},
    defaultSort = null,
  } = {},
) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState(defaultSort?.key ?? null);
  const [sortDir, setSortDir] = useState(defaultSort?.dir ?? null);

  function toggleSort(key) {
    if (key !== sortKey) {
      setSortKey(key);
      setSortDir("asc");
      return;
    }
    const next = NEXT_DIR[String(sortDir)];
    if (next == null) {
      setSortKey(null);
      setSortDir(null);
    } else {
      setSortDir(next);
    }
  }

  const derived = useMemo(() => {
    let filtered = applyQuery(rows, query, { fields: filterFields });

    // Each predicate group is ANDed with the field qualifiers above and with
    // every other group; within a group the selected options are ORed (a
    // multi-select). Query values are lowercased by the parser, so match option
    // keys case-insensitively.
    for (const [groupKey, options] of Object.entries(predicateFilters)) {
      const selected = getQueryFilters(query, groupKey);
      if (selected.length === 0) continue;
      const preds = Object.entries(options)
        .filter(([k]) => selected.includes(k.toLowerCase()))
        .map(([, pred]) => pred);
      if (preds.length > 0) {
        filtered = filtered.filter((row) => preds.some((p) => p(row)));
      }
    }

    if (!sortKey || !sortDir || !sortFields[sortKey]) return filtered;

    const accessor = sortFields[sortKey];
    const factor = sortDir === "desc" ? -1 : 1;
    // Stable sort: decorate with original index and break ties by it.
    return filtered
      .map((row, i) => [row, i])
      .sort(([a, ai], [b, bi]) => {
        const av = accessor(a);
        const bv = accessor(b);
        const aNil = isNil(av);
        const bNil = isNil(bv);
        // Nulls always sort last, independent of direction.
        if (aNil || bNil) {
          if (aNil && bNil) return ai - bi;
          return aNil ? 1 : -1;
        }
        const c = compare(av, bv);
        return c !== 0 ? c * factor : ai - bi;
      })
      .map(([row]) => row);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, query, sortKey, sortDir]);

  return { query, setQuery, sortKey, sortDir, toggleSort, rows: derived };
}
