import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { uploadFile, replaceFile, deleteFile, getFileType } from "@/lib/fileApi";

describe("getFileType", () => {
  it("classifies audio formats the transcribe task accepts", () => {
    for (const ext of [".wav", ".mp3", ".flac", ".m4a", ".ogg", ".webm"]) {
      expect(getFileType(`recording${ext}`)).toBe("audio");
    }
  });

  it("classifies from a full path, not just a bare name", () => {
    expect(getFileType("/scratch/data/audio_001.flac")).toBe("audio");
  });

  it("classifies text and image, and returns null for unknown", () => {
    expect(getFileType("out.txt")).toBe("text");
    expect(getFileType("frame.png")).toBe("image");
    expect(getFileType("archive.zip")).toBeNull();
  });
});

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

function makeOkResponse() {
  return {
    ok: true,
    json: async () => ({}),
    text: async () => "",
  };
}

describe("fileApi URL construction", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn(async () => makeOkResponse());
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("uploadFile", () => {
    it("omits profile param for null profile", async () => {
      const file = new File([], "test.png", { type: "image/png" });
      await uploadFile("/tmp/test.png", file, null);
      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/image`);
    });

    it("omits profile param for a local profile", async () => {
      const file = new File([], "test.png", { type: "image/png" });
      await uploadFile("/tmp/test.png", file, LOCAL_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/image`);
    });

    it("omits profile param for a Slurm-localhost profile", async () => {
      const file = new File([], "test.png", { type: "image/png" });
      await uploadFile("/tmp/test.png", file, SLURM_LOCALHOST_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/image`);
    });

    it("includes profile param for a remote Slurm profile", async () => {
      const file = new File([], "test.png", { type: "image/png" });
      await uploadFile("/tmp/test.png", file, SLURM_REMOTE_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(
        `${BASE_URL}/api/image?profile=della`
      );
    });
  });

  describe("replaceFile", () => {
    it("omits profile param for null profile", async () => {
      const file = new File([], "new.png", { type: "image/png" });
      await replaceFile("/tmp/test.png", file, null);
      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/image`);
    });

    it("omits profile param for a local profile", async () => {
      const file = new File([], "new.png", { type: "image/png" });
      await replaceFile("/tmp/test.png", file, LOCAL_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/image`);
    });

    it("omits profile param for a Slurm-localhost profile", async () => {
      const file = new File([], "new.png", { type: "image/png" });
      await replaceFile("/tmp/test.png", file, SLURM_LOCALHOST_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/image`);
    });

    it("includes profile param for a remote Slurm profile", async () => {
      const file = new File([], "new.png", { type: "image/png" });
      await replaceFile("/tmp/test.png", file, SLURM_REMOTE_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(
        `${BASE_URL}/api/image?profile=della`
      );
    });
  });

  describe("deleteFile", () => {
    it("omits profile param for null profile", async () => {
      await deleteFile("/tmp/test.png", null);
      expect(fetchMock.mock.calls[0][0]).toBe(
        `${BASE_URL}/api/image?path=${encodeURIComponent("/tmp/test.png")}`
      );
    });

    it("omits profile param for a local profile", async () => {
      await deleteFile("/tmp/test.png", LOCAL_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(
        `${BASE_URL}/api/image?path=${encodeURIComponent("/tmp/test.png")}`
      );
    });

    it("omits profile param for a Slurm-localhost profile", async () => {
      await deleteFile("/tmp/test.png", SLURM_LOCALHOST_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(
        `${BASE_URL}/api/image?path=${encodeURIComponent("/tmp/test.png")}`
      );
    });

    it("includes profile param for a remote Slurm profile", async () => {
      await deleteFile("/tmp/test.png", SLURM_REMOTE_PROFILE);
      expect(fetchMock.mock.calls[0][0]).toBe(
        `${BASE_URL}/api/image?path=${encodeURIComponent("/tmp/test.png")}&profile=della`
      );
    });
  });
});
