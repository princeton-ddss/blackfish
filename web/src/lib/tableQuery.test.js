import { describe, test, expect } from "vitest";
import {
  parseQuery,
  applyQuery,
  setQueryFilter,
  setQueryFilters,
  toggleQueryFilter,
  getQueryFilter,
  getQueryFilters,
} from "./tableQuery";

describe("parseQuery", () => {
  test("empty input yields empty text and filters", () => {
    expect(parseQuery("")).toEqual({ text: [], filters: {} });
    expect(parseQuery(null)).toEqual({ text: [], filters: {} });
  });

  test("splits bare terms and key:value qualifiers", () => {
    expect(parseQuery("status:failed whisper report")).toEqual({
      text: ["whisper", "report"],
      filters: { status: ["failed"] },
    });
  });

  test("lowercases keys, values, and bare terms", () => {
    expect(parseQuery("Status:Failed Whisper")).toEqual({
      text: ["whisper"],
      filters: { status: ["failed"] },
    });
  });

  test("repeating a key accumulates values (OR within a key)", () => {
    expect(parseQuery("status:failed status:success")).toEqual({
      text: [],
      filters: { status: ["failed", "success"] },
    });
  });

  test("quoted values preserve spaces", () => {
    expect(parseQuery('name:"my job" foo')).toEqual({
      text: ["foo"],
      filters: { name: ["my job"] },
    });
  });

  test("a leading colon is treated as free text, not a qualifier", () => {
    expect(parseQuery(":oops")).toEqual({ text: [":oops"], filters: {} });
  });

  test("a trailing colon with no value is free text", () => {
    expect(parseQuery("status:")).toEqual({ text: ["status:"], filters: {} });
  });
});

describe("applyQuery", () => {
  const rows = [
    { input_file: "a/one.wav", output_file: "out/one.txt", status: "success" },
    { input_file: "a/two.wav", output_file: null, status: "failed" },
    { input_file: "b/three.mp3", output_file: "out/three.txt", status: "success" },
  ];
  const config = {
    fields: {
      status: (r) => r.status,
      file: (r) => r.input_file,
      out: (r) => r.output_file,
    },
  };

  test("no query returns all rows unchanged", () => {
    expect(applyQuery(rows, "", config)).toBe(rows);
  });

  test("bare text does not filter (qualifier-only)", () => {
    // "three" has no key: — it's ignored, so all rows come back.
    expect(applyQuery(rows, "three", config)).toBe(rows);
  });

  test("a partial key (no colon yet) is ignored, returning all rows", () => {
    expect(applyQuery(rows, "stat", config)).toBe(rows);
  });

  test("a key with no value yet is ignored, returning all rows", () => {
    // `status:` mid-typing must not filter or show an empty result.
    expect(applyQuery(rows, "status:", config)).toBe(rows);
  });

  test("an unknown key is ignored (not a failed match), returning all rows", () => {
    expect(applyQuery(rows, "bogus:x", config)).toBe(rows);
  });

  test("a complete known qualifier filters by its mapped field", () => {
    expect(applyQuery(rows, "status:failed", config)).toEqual([rows[1]]);
  });

  test("qualifier values OR within a key", () => {
    expect(applyQuery(rows, "status:failed status:success", config)).toEqual(
      rows,
    );
  });

  test("qualifiers across keys AND together", () => {
    expect(applyQuery(rows, "status:success file:three", config)).toEqual([
      rows[2],
    ]);
  });

  test("known qualifiers apply even alongside ignored bare/partial tokens", () => {
    expect(applyQuery(rows, "three status:failed stat", config)).toEqual([
      rows[1],
    ]);
  });

  test("a null mapped field never matches a qualifier value", () => {
    // row[1] has output_file null; filtering on it should exclude it.
    expect(applyQuery(rows, "out:one", config)).toEqual([rows[0]]);
  });

  test("qualifier values match as case-insensitive substrings", () => {
    expect(applyQuery(rows, "file:THR", config)).toEqual([rows[2]]);
    expect(applyQuery(rows, "status:fail", config)).toEqual([rows[1]]);
  });
});

describe("setQueryFilter / getQueryFilter", () => {
  test("sets a qualifier on an empty query", () => {
    expect(setQueryFilter("", "status", "failed")).toBe("status:failed");
  });

  test("replaces an existing value for the same key", () => {
    expect(setQueryFilter("status:success foo", "status", "failed")).toBe(
      "foo status:failed",
    );
  });

  test("clearing removes the qualifier but keeps the rest", () => {
    expect(setQueryFilter("foo status:failed bar", "status", null)).toBe(
      "foo bar",
    );
  });

  test("quotes values containing spaces", () => {
    expect(setQueryFilter("", "name", "my job")).toBe('name:"my job"');
  });

  test("getQueryFilter reads the current value or null", () => {
    expect(getQueryFilter("a status:failed b", "status")).toBe("failed");
    expect(getQueryFilter("a b", "status")).toBeNull();
  });

  test("round-trips through set then get", () => {
    const q = setQueryFilter("keep me", "status", "success");
    expect(getQueryFilter(q, "status")).toBe("success");
  });
});

describe("multi-value filters", () => {
  test("setQueryFilters writes several values for one key", () => {
    expect(setQueryFilters("keep", "status", ["running", "stopped"])).toBe(
      "keep status:running status:stopped",
    );
  });

  test("setQueryFilters with an empty array removes the key", () => {
    expect(setQueryFilters("a status:running b", "status", [])).toBe("a b");
  });

  test("getQueryFilters returns all values for a key", () => {
    expect(getQueryFilters("status:running status:stopped x", "status")).toEqual(
      ["running", "stopped"],
    );
    expect(getQueryFilters("x", "status")).toEqual([]);
  });

  test("toggleQueryFilter adds a value when absent", () => {
    expect(toggleQueryFilter("status:running", "status", "stopped")).toBe(
      "status:running status:stopped",
    );
  });

  test("toggleQueryFilter removes a value when present, keeping the rest", () => {
    expect(
      toggleQueryFilter("status:running status:stopped", "status", "running"),
    ).toBe("status:stopped");
  });

  test("multiple values for a key OR together in applyQuery", () => {
    const cfg = { fields: { status: (r) => r.status } };
    const data = [
      { status: "running" },
      { status: "stopped" },
      { status: "pending" },
    ];
    expect(applyQuery(data, "status:running status:pending", cfg)).toEqual([
      data[0],
      data[2],
    ]);
  });
});
