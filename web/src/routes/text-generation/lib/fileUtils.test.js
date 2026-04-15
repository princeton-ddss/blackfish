import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { fetchRemoteText } from "./fileUtils";

const BASE_URL = "http://localhost:8000";

const LOCAL_PROFILE = {
  name: "local",
  schema: "local",
  home_dir: "/home/u",
  cache_dir: "/cache",
};

const SLURM_LOCALHOST_PROFILE = {
  name: "ondemand",
  schema: "slurm",
  host: "localhost",
  user: "u",
  home_dir: "/home/u/.blackfish-ondemand",
  cache_dir: "/cache",
};

const SLURM_REMOTE_PROFILE = {
  name: "della",
  schema: "slurm",
  host: "della.princeton.edu",
  user: "u",
  home_dir: "/home/u/.blackfish",
  cache_dir: "/cache",
};

function makeOkResponse(text = "") {
  return {
    ok: true,
    status: 200,
    text: async () => text,
  };
}

describe("fetchRemoteText URL construction", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn(async () => makeOkResponse("contents"));
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("omits profile param for null profile", async () => {
    await fetchRemoteText("/tmp/notes.md", null);
    expect(fetchMock.mock.calls[0][0]).toBe(
      `${BASE_URL}/api/text?path=${encodeURIComponent("/tmp/notes.md")}`
    );
  });

  it("omits profile param for a local profile", async () => {
    await fetchRemoteText("/tmp/notes.md", LOCAL_PROFILE);
    expect(fetchMock.mock.calls[0][0]).toBe(
      `${BASE_URL}/api/text?path=${encodeURIComponent("/tmp/notes.md")}`
    );
  });

  it("omits profile param for a Slurm-localhost profile", async () => {
    await fetchRemoteText("/tmp/notes.md", SLURM_LOCALHOST_PROFILE);
    expect(fetchMock.mock.calls[0][0]).toBe(
      `${BASE_URL}/api/text?path=${encodeURIComponent("/tmp/notes.md")}`
    );
  });

  it("includes profile param for a remote Slurm profile", async () => {
    await fetchRemoteText("/tmp/notes.md", SLURM_REMOTE_PROFILE);
    expect(fetchMock.mock.calls[0][0]).toBe(
      `${BASE_URL}/api/text?path=${encodeURIComponent("/tmp/notes.md")}&profile=della`
    );
  });
});
