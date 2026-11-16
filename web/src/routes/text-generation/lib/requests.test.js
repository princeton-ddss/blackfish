import { afterEach, describe, expect, it, vi } from "vitest";
import { blackfishApiURL } from "@/config";
import { streamChatCompletionInference, streamCompletionInference } from "./requests";

const encoder = new TextEncoder();
const service = { port: 8123 };
const variants = [
  {
    name: "chat",
    run: (proxy = false, signal) => streamChatCompletionInference(
      service, [{ role: "user", content: "Hello" }], { stream: true }, proxy, signal
    ),
    event: (text) => ({ choices: [{ delta: { content: text } }] }),
    endpoint: "chat/completions",
  },
  {
    name: "completion",
    run: (proxy = false) => streamCompletionInference(service, "Hello", { stream: true }, proxy),
    event: (text) => ({ choices: [{ text }] }),
    endpoint: "completions",
  },
];

function streamResponse(chunks, { close = true } = {}) {
  const cancel = vi.fn();
  let controller;
  const queue = [...chunks];
  const body = new ReadableStream({
    start(value) { controller = value; },
    pull(value) {
      if (queue.length) value.enqueue(queue.shift());
      else if (close) value.close();
    },
    cancel,
  });
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, body });
  vi.stubGlobal("fetch", fetchMock);
  return { body, cancel, controller, fetchMock };
}

async function collect(stream) {
  const events = [];
  for await (const batch of stream) {
    expect(Array.isArray(batch)).toBe(true);
    expect(batch.length).toBeGreaterThan(0);
    events.push(...batch);
  }
  return events;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe.each(variants)("$name streaming", ({ run, event, endpoint }) => {
  it.each(["\n", "\r\n"])("preserves every byte split with %j separators", async (newline) => {
    const expected = event("Orcas 🐋 café");
    const bytes = encoder.encode(`data: ${JSON.stringify(expected)}${newline}${newline}`);
    for (let split = 1; split < bytes.length; split += 1) {
      const { body } = streamResponse([bytes.slice(0, split), bytes.slice(split)]);
      expect(await collect(run()), `split at byte ${split}`).toEqual([expected]);
      expect(body.locked).toBe(false);
    }
  });

  it("preserves order across byte-sized reads and coalesced events", async () => {
    const expected = [event("one"), event("two"), event("three")];
    const first = encoder.encode(`data: ${JSON.stringify(expected[0])}\n\n`);
    const rest = encoder.encode(expected.slice(1).map((value) => `data: ${JSON.stringify(value)}\n\n`).join(""));
    streamResponse([...first].map((byte) => Uint8Array.of(byte)).concat([rest]));
    expect(await collect(run())).toEqual(expected);
  });

  it("ignores SSE comments and metadata and joins data fields", async () => {
    const expected = event("hello");
    const json = JSON.stringify(expected);
    streamResponse([encoder.encode(`: keepalive\n\nevent: message\nid: 1\nretry: 1000\ndata:${json.slice(0, 1)}\ndata: ${json.slice(1)}\n\n`)]);
    expect(await collect(run())).toEqual([expected]);
  });

  it("stops at DONE without emitting synthetic or subsequent events", async () => {
    const expected = event("hello");
    const { body, cancel } = streamResponse([encoder.encode(
      `data: ${JSON.stringify(expected)}\n\ndata: [DONE]\n\ndata: invalid\n\n`
    )], { close: false });
    expect(await collect(run())).toEqual([expected]);
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
  });

  it("handles DONE split across reads", async () => {
    streamResponse([encoder.encode("data: [DO"), encoder.encode("NE]\n\n")]);
    expect(await collect(run())).toEqual([]);
  });

  it("rejects malformed complete events and cancels the reader", async () => {
    const { body, cancel } = streamResponse([encoder.encode("data: invalid\n\n")], { close: false });
    await expect(collect(run())).rejects.toThrow("Invalid JSON in inference stream");
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
  });

  it("reports an unfinished event at EOF instead of parsing it", async () => {
    const { body } = streamResponse([encoder.encode(`data: ${JSON.stringify(event("hello"))}\n`)]);
    await expect(collect(run())).rejects.toThrow("incomplete event");
    expect(body.locked).toBe(false);
  });

  it("keeps completed events before reporting a truncated following event", async () => {
    const expected = event("hello");
    streamResponse([encoder.encode(`data: ${JSON.stringify(expected)}\n\ndata: {`)]);
    const stream = run();
    expect((await stream.next()).value).toEqual([expected]);
    await expect(stream.next()).rejects.toThrow("incomplete event");
  });

  it.each([
    { object: "error", message: "bad request", code: 422 },
    { type: "BadRequestError", message: "bad request", code: 422 },
  ])("preserves in-stream service errors: %j", async (error) => {
    const { body, cancel } = streamResponse([encoder.encode(`data: ${JSON.stringify(error)}\n\n`)], { close: false });
    await expect(collect(run())).rejects.toMatchObject({ message: "bad request", status: 422 });
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
  });

  it("provides fallback details for an in-stream service error", async () => {
    streamResponse([encoder.encode('data: {"object":"error"}\n\n')]);
    await expect(collect(run())).rejects.toMatchObject({
      message: "Service returned an error.", status: 500,
    });
  });

  it("preserves a fetch failure", async () => {
    const error = new TypeError("Failed to fetch");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));
    await expect(collect(run())).rejects.toBe(error);
  });

  it("preserves transport read errors and releases the reader", async () => {
    const { body, controller } = streamResponse([], { close: false });
    const pending = collect(run());
    const assertion = expect(pending).rejects.toThrow("connection lost");
    controller.error(new Error("connection lost"));
    await assertion;
    expect(body.locked).toBe(false);
  });

  it("cancels and releases the reader when the consumer exits early", async () => {
    const expected = event("hello");
    const { body, cancel } = streamResponse([encoder.encode(`data: ${JSON.stringify(expected)}\n\n`)], { close: false });
    const stream = run();
    expect((await stream.next()).value).toEqual([expected]);
    await stream.return();
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
  });

  it("does not let cancellation failure mask the parsing error", async () => {
    const { body, cancel } = streamResponse([encoder.encode("data: invalid\n\n")], { close: false });
    cancel.mockRejectedValue(new Error("cancel failed"));
    await expect(collect(run())).rejects.toThrow("Invalid JSON in inference stream");
    expect(body.locked).toBe(false);
  });

  it("rejects a response without a readable body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body: null }));
    await expect(collect(run())).rejects.toThrow("no readable body");
  });

  it.each([false, true])("preserves request routing and payloads (proxy=%s)", async (proxy) => {
    const { fetchMock } = streamResponse([]);
    expect(await collect(run(proxy))).toEqual([]);
    const [url, options] = fetchMock.mock.calls[0];
    const base = proxy ? `${blackfishApiURL}/proxy/8123` : "http://127.0.0.1:8123";
    expect(url).toBe(`${base}/v1/${endpoint}${proxy ? "?streaming=true" : ""}`);
    expect(options.method).toBe("POST");
    expect(options.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(options.body)).toEqual(endpoint === "completions"
      ? { prompt: "Hello", stream: true, do_sample: true }
      : { messages: [{ role: "user", content: "Hello" }], stream: true });
  });

  it.each([
    [JSON.stringify({ detail: "CPU inference timed out" }), "CPU inference timed out"],
    ["upstream unavailable", "Stream request failed."],
  ])("preserves HTTP error details and status", async (body, message) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status: 504 })));
    await expect(collect(run())).rejects.toMatchObject({ message, status: 504 });
  });
});

describe("chat cancellation", () => {
  it.each([false, true])("aborts a pending read even if cancellation fails (%s)", async (cancelFails) => {
    const { body, cancel, fetchMock } = streamResponse([], { close: false });
    if (cancelFails) cancel.mockRejectedValue(new Error("cancel failed"));
    const controller = new AbortController();
    const pending = collect(variants[0].run(false, controller.signal));
    const assertion = expect(pending).rejects.toMatchObject({ name: "AbortError" });
    // Wait until fetch has resolved and the generator has acquired the reader.
    await vi.waitFor(() => expect(body.locked).toBe(true));
    expect(fetchMock.mock.calls[0][1].signal).toBe(controller.signal);
    controller.abort();
    await assertion;
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
  });

  it("rejects an already-aborted signal without starting a request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    controller.abort();
    await expect(collect(variants[0].run(false, controller.signal)))
      .rejects.toMatchObject({ name: "AbortError" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("does not emit buffered events after aborting between yields", async () => {
    const expected = variants[0].event("first");
    const next = variants[0].event("second");
    const { body, cancel } = streamResponse([encoder.encode(
      `data: ${JSON.stringify(expected)}\n\ndata: ${JSON.stringify(next)}\n\n`
    )], { close: false });
    const controller = new AbortController();
    const stream = variants[0].run(false, controller.signal);
    expect((await stream.next()).value).toEqual([expected]);
    controller.abort();
    await expect(stream.next()).rejects.toMatchObject({ name: "AbortError" });
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
  });
});
