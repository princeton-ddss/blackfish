import { describe, it, expect, vi, afterEach } from "vitest";
import { buildContainerConfig, setDefaultProfile, resumeJob } from "@/lib/requests";

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

describe("resumeJob", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("PUTs to the job's resume endpoint and returns the updated job", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "job-001", status: "resubmitted" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await resumeJob("job-001");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/jobs/job-001/resume");
    expect(options.method).toBe("PUT");
    expect(result).toEqual({ id: "job-001", status: "resubmitted" });
  });

  it("throws the server detail so the caller can show why a resume was refused", async () => {
    // e.g. a job whose input_dir was deleted since it ran, or a BROKEN job.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Input directory does not exist" }),
      })
    );

    await expect(resumeJob("job-001")).rejects.toThrow(
      "Input directory does not exist"
    );
  });

  it("falls back to a generic message when the body has no detail", async () => {
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

    await expect(resumeJob("job-001")).rejects.toThrow("Failed to resume job");
  });
});
