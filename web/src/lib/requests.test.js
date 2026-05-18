import { describe, it, expect, vi, afterEach } from "vitest";
import { buildContainerConfig, setDefaultProfile } from "@/lib/requests";

describe("buildContainerConfig", () => {
  it("strips disable_thinking when false and adds no launch_kwargs", () => {
    const out = buildContainerConfig({
      disable_thinking: false,
      disable_custom_kernels: false,
      input_dir: "/data",
    });
    expect(out).toEqual({
      disable_custom_kernels: false,
      input_dir: "/data",
    });
    expect(out).not.toHaveProperty("disable_thinking");
    expect(out).not.toHaveProperty("launch_kwargs");
  });

  it("translates disable_thinking=true into launch_kwargs and strips the flag", () => {
    const out = buildContainerConfig({
      disable_thinking: true,
      disable_custom_kernels: false,
    });
    expect(out).not.toHaveProperty("disable_thinking");
    expect(out.launch_kwargs).toBe(
      `--default-chat-template-kwargs '{"enable_thinking": false, "thinking": false}'`
    );
    expect(out.disable_custom_kernels).toBe(false);
  });
});

describe("setDefaultProfile", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("PUTs to the encoded profile default endpoint and returns the body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ name: "my profile", default: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await setDefaultProfile("my profile");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/profiles/my%20profile/default");
    expect(options).toEqual({ method: "PUT" });
    expect(result).toEqual({ name: "my profile", default: true });
  });

  it("throws the server detail message on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Profile not found." }),
      })
    );

    await expect(setDefaultProfile("missing")).rejects.toMatchObject({
      message: "Profile not found.",
      status: 404,
    });
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("not json");
        },
      })
    );

    await expect(setDefaultProfile("broken")).rejects.toMatchObject({
      message: "Failed to set default profile.",
      status: 500,
    });
  });
});
