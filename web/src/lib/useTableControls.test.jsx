import { describe, test, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTableControls } from "./useTableControls";

const rows = [
  { name: "beta", size: 2, when: "2026-01-02T00:00:00Z" },
  { name: "alpha", size: 10, when: "2026-01-01T00:00:00Z" },
  { name: "gamma", size: null, when: null },
];

const config = {
  filterFields: { name: (r) => r.name },
  sortFields: {
    name: (r) => r.name,
    size: (r) => r.size,
    when: (r) => r.when,
  },
};

describe("useTableControls", () => {
  test("returns all rows unsorted with no query or sort", () => {
    const { result } = renderHook(() => useTableControls(rows, config));
    expect(result.current.rows).toEqual(rows);
  });

  test("filters by a qualifier in the query string", () => {
    const { result } = renderHook(() => useTableControls(rows, config));
    act(() => result.current.setQuery("name:alph"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["alpha"]);
  });

  test("bare text does not filter (qualifier-only)", () => {
    const { result } = renderHook(() => useTableControls(rows, config));
    act(() => result.current.setQuery("alph"));
    expect(result.current.rows).toEqual(rows);
  });

  test("applies a predicate-filter option selected via <group>:<value>", () => {
    const cfg = {
      ...config,
      predicateFilters: { size: { small: (r) => (r.size ?? Infinity) < 5 } },
    };
    const { result } = renderHook(() => useTableControls(rows, cfg));
    act(() => result.current.setQuery("size:small"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["beta"]);
  });

  test("an unknown predicate-filter value applies nothing", () => {
    const cfg = {
      ...config,
      predicateFilters: { size: { small: (r) => r.size < 5 } },
    };
    const { result } = renderHook(() => useTableControls(rows, cfg));
    act(() => result.current.setQuery("size:bogus"));
    expect(result.current.rows).toEqual(rows);
  });

  test("a predicate filter ANDs with a typed field qualifier", () => {
    const cfg = {
      ...config,
      predicateFilters: { has: { when: (r) => r.when != null } },
    };
    const { result } = renderHook(() => useTableControls(rows, cfg));
    // name:a matches alpha, beta, gamma; has:when drops gamma (null when).
    act(() => result.current.setQuery("name:a has:when"));
    expect(result.current.rows.map((r) => r.name).sort()).toEqual([
      "alpha",
      "beta",
    ]);
  });

  test("multiple options within a group OR together", () => {
    const cfg = {
      ...config,
      predicateFilters: {
        size: {
          small: (r) => (r.size ?? Infinity) < 5,
          big: (r) => (r.size ?? -Infinity) > 8,
        },
      },
    };
    const { result } = renderHook(() => useTableControls(rows, cfg));
    // small -> beta(2); big -> alpha(10); gamma(null) matches neither.
    act(() => result.current.setQuery("size:small size:big"));
    expect(result.current.rows.map((r) => r.name).sort()).toEqual([
      "alpha",
      "beta",
    ]);
  });

  test("options from different groups AND together", () => {
    const cfg = {
      ...config,
      predicateFilters: {
        size: { small: (r) => (r.size ?? Infinity) < 5 },
        has: { when: (r) => r.when != null },
      },
    };
    const { result } = renderHook(() => useTableControls(rows, cfg));
    // small -> beta, gamma(null->Infinity excluded); when -> beta, alpha.
    act(() => result.current.setQuery("size:small has:when"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["beta"]);
  });

  test("toggles a column asc -> desc -> off", () => {
    const { result } = renderHook(() => useTableControls(rows, config));

    act(() => result.current.toggleSort("name"));
    expect(result.current.sortDir).toBe("asc");
    expect(result.current.rows.map((r) => r.name)).toEqual([
      "alpha",
      "beta",
      "gamma",
    ]);

    act(() => result.current.toggleSort("name"));
    expect(result.current.sortDir).toBe("desc");
    expect(result.current.rows.map((r) => r.name)).toEqual([
      "gamma",
      "beta",
      "alpha",
    ]);

    act(() => result.current.toggleSort("name"));
    expect(result.current.sortDir).toBeNull();
    expect(result.current.rows).toEqual(rows); // back to original order
  });

  test("sorts numbers numerically with nulls last", () => {
    const { result } = renderHook(() => useTableControls(rows, config));
    act(() => result.current.toggleSort("size")); // asc
    expect(result.current.rows.map((r) => r.size)).toEqual([2, 10, null]);
  });

  test("nulls sort last even when descending", () => {
    const { result } = renderHook(() => useTableControls(rows, config));
    act(() => result.current.toggleSort("size"));
    act(() => result.current.toggleSort("size")); // desc
    expect(result.current.rows.map((r) => r.size)).toEqual([10, 2, null]);
  });

  test("sorts date-like strings chronologically", () => {
    const { result } = renderHook(() => useTableControls(rows, config));
    act(() => result.current.toggleSort("when")); // asc
    expect(result.current.rows.map((r) => r.name)).toEqual([
      "alpha",
      "beta",
      "gamma", // null when -> last
    ]);
  });

  test("honors a default sort", () => {
    const { result } = renderHook(() =>
      useTableControls(rows, { ...config, defaultSort: { key: "name", dir: "desc" } }),
    );
    expect(result.current.rows.map((r) => r.name)).toEqual([
      "gamma",
      "beta",
      "alpha",
    ]);
  });
});
