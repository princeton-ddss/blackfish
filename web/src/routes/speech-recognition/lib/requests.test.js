import { describe, it, expect, vi, afterEach } from "vitest";

import { callSpeechRecognitionInference } from "./requests";

const service = { port: 8080, mount: "/scratch/gpfs/xxx/audio" };
const audioPath = "/scratch/gpfs/xxx/audio/sample.wav";

function stubFetchOk() {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ text: "hello" }),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("callSpeechRecognitionInference language handling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the lowercased language name for an explicit selection", async () => {
    const fetchMock = stubFetchOk();

    await callSpeechRecognitionInference(service, audioPath, {
      language: { id: 3, name: "Portuguese" },
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.language).toBe("portuguese");
  });

  it("omits the language field when Auto-detect is chosen", async () => {
    const fetchMock = stubFetchOk();

    await callSpeechRecognitionInference(service, audioPath, {
      language: { id: 0, name: "Auto-detect" },
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body).not.toHaveProperty("language");
    // The other required fields should still be populated.
    expect(body.audio_path).toBe("/data/audio/sample.wav");
    expect(body.response_format).toBe("text");
  });
});
