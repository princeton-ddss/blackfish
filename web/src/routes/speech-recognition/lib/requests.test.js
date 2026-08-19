import { describe, it, expect, vi, afterEach } from "vitest";
import { callSpeechRecognitionInference } from "./requests";

const service = { port: 8080, mount: "/mnt/audio", id: "svc-1" };
const params = { language: { name: "English" } };

describe("callSpeechRecognitionInference", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed body on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ text: " hello " }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await callSpeechRecognitionInference(
      service,
      "/mnt/audio/clip.wav",
      params,
      true,
    );

    expect(res).toEqual({ text: " hello " });
  });

  it("surfaces the status and backend detail on a 504 timeout", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 504,
      json: async () => ({ detail: "The service took too long to respond." }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      callSpeechRecognitionInference(service, "/mnt/audio/clip.wav", params, true),
    ).rejects.toMatchObject({
      status: 504,
      message: "The service took too long to respond.",
    });
  });

  it("falls back to a generic message when the error body has no JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      callSpeechRecognitionInference(service, "/mnt/audio/clip.wav", params, true),
    ).rejects.toMatchObject({
      status: 500,
      message: "Failed to call the service",
    });
  });
});
