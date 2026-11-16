import { blackfishApiURL } from "@/config";
import { parseErrorResponse } from "@/lib/requests";

/** Extract SSE data fields, ignoring comments and other event metadata. */
function eventData(event) {
  return event.split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).replace(/^ /, ""))
    .join("\n");
}

/** Parse JSON event data, preserving the message and status of service errors. */
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
 * @param {string} url - Direct service or backend proxy URL.
 * @param {string} body - JSON-encoded inference request.
 * @param {AbortSignal} [signal] - Cancels the request and any pending read.
 * @yields {Array<object>} Parsed events in server order.
 * @throws {Error} On HTTP, service, transport, or event framing/parsing errors.
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
  // Cancel a pending read as well as the fetch. Repeating cancel in finally is
  // harmless: the stream invokes its underlying cancel operation only once.
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

/**
 * Call a completion service using streaming inference.
 * @param {object} service - The service to call, including its port.
 * @param {string} prompt - The prompt to send.
 * @param {object} params - Inference options, including the stream flag.
 * @param {boolean} [use_proxy=false] - Use the backend proxy instead of localhost.
 * @returns {AsyncGenerator<Array<object>>} Arrays of parsed completion events.
 * @throws {Error} On HTTP, service, transport, malformed, or truncated responses.
 */
export async function* streamCompletionInference(service, prompt, params, use_proxy = false) {
  const body = JSON.stringify({ prompt, ...params, do_sample: true });
  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/completions`;
  yield* streamInference(url, body);
}

/**
 * Call a chat service using streaming inference.
 * @param {object} service - The service to call, including its port.
 * @param {Array<object>} messages - Conversation messages to send.
 * @param {object} params - Inference options, including the stream flag.
 * @param {boolean} [use_proxy=false] - Use the backend proxy instead of localhost.
 * @param {AbortSignal} [signal] - Cancels the request and any pending read.
 * @returns {AsyncGenerator<Array<object>>} Arrays of parsed chat events.
 * @throws {Error} On HTTP, service, transport, malformed, or truncated responses.
 * An aborted signal propagates its abort reason.
 */
export async function* streamChatCompletionInference(service, messages, params, use_proxy = false, signal = undefined) {
  const body = JSON.stringify({ messages, ...params });
  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/chat/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/chat/completions`;
  yield* streamInference(url, body, signal);
}
