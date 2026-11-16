import { blackfishApiURL } from "@/config";
import { parseErrorResponse } from "@/lib/requests";

/** Extract SSE data fields, ignoring comments and other event metadata. */
function eventData(event) {
  return event.split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).replace(/^ /, ""))
    .join("\n");
}

function parseEvent(data) {
  let parsed;
  try {
    parsed = JSON.parse(data);
  } catch {
    throw new Error("Invalid JSON in inference stream.");
  }
  if (parsed.object === "error" || parsed.type === "BadRequestError") {
    const error = new Error(parsed.message || "Service returned an error.");
    error.status = parsed.code || 500;
    throw error;
  }
  return parsed;
}

/**
 * Read complete SSE events independently of network read boundaries.
 * Malformed JSON and unterminated events at EOF are errors: neither should
 * silently turn damaged inference output into a successful response.
 */
async function* streamInference(url, body, signal) {
  signal?.throwIfAborted();
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    signal,
  });
  if (!res.ok) throw await parseErrorResponse(res, "Stream request failed.");
  if (!res.body) throw new Error("Inference response has no readable body.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let ended = false;
  // Cancel a pending read as well as the fetch, including for controlled streams.
  const abort = () => { reader.cancel().catch(() => {}); };
  signal?.addEventListener("abort", abort, { once: true });
  try {
    while (true) {
      signal?.throwIfAborted();
      const { value, done } = await reader.read();
      signal?.throwIfAborted();
      if (done) {
        ended = true;
        buffer += decoder.decode();
        if (buffer.trim()) throw new Error("Inference stream ended with an incomplete event.");
        return;
      }
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer)) !== null) {
        signal?.throwIfAborted();
        const event = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        const data = eventData(event);
        if (!data) continue;
        if (data === "[DONE]") return;
        // Keep the array-of-events interface consumed by both components.
        yield [parseEvent(data)];
      }
    }
  } finally {
    signal?.removeEventListener("abort", abort);
    try {
      if (!ended) await reader.cancel();
    } catch {
      // Cleanup must not mask the original service, parsing, or transport error.
    } finally {
      reader.releaseLock();
    }
  }
}

/** Stream OpenAI-compatible completion events, directly or through the proxy. */
export async function* streamCompletionInference(service, prompt, params, use_proxy = false) {
  const body = JSON.stringify({ prompt, ...params, do_sample: true });
  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/completions`;
  yield* streamInference(url, body);
}

/** Stream OpenAI-compatible chat events, preserving the caller's abort signal. */
export async function* streamChatCompletionInference(service, messages, params, use_proxy = false, signal = undefined) {
  const body = JSON.stringify({ messages, ...params });
  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/chat/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/chat/completions`;
  yield* streamInference(url, body, signal);
}
