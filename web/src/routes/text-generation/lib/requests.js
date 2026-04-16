import { blackfishApiURL } from "@/config";

/**
 * Parse an error response from a streaming request.
 * @param {Response} res - The fetch response object.
 * @returns {Promise<Error>} An error with the parsed message and status code.
 */
async function parseErrorResponse(res) {
  let errorMessage = "Stream request failed.";
  try {
    const errorBody = await res.json();
    errorMessage = errorBody.detail || errorBody.message || errorMessage;
  } catch {
    // Response body may not be JSON
  }
  const error = new Error(errorMessage);
  error.status = res.status;
  return error;
}

/**
 * Parse a single SSE chunk from a streaming response.
 * @param {string} chunk - A raw SSE chunk (without the trailing blank line).
 * @returns {object|null} Parsed chunk, or null if the chunk should be skipped.
 * @throws {Error} If the parsed chunk represents a service error.
 */
function parseStreamChunk(chunk) {
  if (chunk === 'data: [DONE]') {
    return { choices: [{ delta: { content: "" } }] };
  }

  let parsed;
  try {
    parsed = JSON.parse(chunk.replace('data: {', '{'));
  } catch {
    console.warn("Failed to parse SSE chunk:", chunk);
    return null;
  }

  if (parsed.object === "error" || parsed.type === "BadRequestError") {
    const error = new Error(parsed.message || "Service returned an error.");
    error.status = parsed.code || 500;
    throw error;
  }

  return parsed;
}

/**
 * Call a completion service with given ID using streaming inference.
 * @param {object} service - The service object to call.
 * @param {string} prompt - The prompt to send.
 * @param {object} params - Extra options to send.
 * @param {boolean} [use_proxy=false] - `true` uses the `blackfishApiURL`, otherwise, `localhost`.
 * @return {object} Completion service data.
 */
export async function* streamCompletionInference(service, prompt, params, use_proxy=false) {

  const body = JSON.stringify({
    prompt: prompt,
    ...params,
    do_sample: true,
  });

  console.debug("Starting completion stream with request:", JSON.parse(body));

  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/completions`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }

  const reader = res.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      console.debug("Stream done.");
      break;
    }

    const chunks = decoder.decode(value, { stream: true }).split('\n\n');
    console.debug("Received chunks:", chunks);
    const data = [];
    for (const x of chunks.filter(c => c !== '')) {
      const parsed = parseStreamChunk(x);
      if (parsed !== null) {
        data.push(parsed);
      }
    }

    yield data;
  }
}

/**
 * Call a text generation service with given ID using streaming inference.
 * @param {object} service
 * @param {string} inputs
 * @param {object} params
 * @param {boolean} [use_proxy=false]
 * @return {object}
 */
export async function* streamTextGenerationInference(service, inputs, params, use_proxy=false) {

  params.do_sample = true;

  const body = JSON.stringify({
    inputs: inputs,
    parameters: params,
  });

  console.debug("Starting text generation stream with request:", JSON.parse(body));

  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/generate_stream?streaming=true`
    : `http://127.0.0.1:${service.port}/generate_stream`
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }

  const reader = res.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      console.debug("Stream done.");
      break;
    }

    const chunks = decoder.decode(value, { stream: true }).split('\n\n');
    console.debug("Received chunks:", chunks);
    const data = chunks.filter(x => x !== '').map(x => JSON.parse(x.replace('data: ', '')));

    yield data;
  }
}

/**
 * Call a chat service with given ID using streaming inference.
 * @param {object} service
 * @param {string} messages
 * @param {object} params
 * @param {boolean} [use_proxy=false]
 * @return {object}
 */
export async function* streamChatCompletionInference(service, messages, params, use_proxy=false, signal=undefined) {

  const body = JSON.stringify({
    messages: messages,
    ...params,
  });

  console.debug("Starting chat completion stream with request:", JSON.parse(body));

  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/chat/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/chat/completions`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body,
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }

  const reader = res.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      console.debug("Stream done.");
      break;
    }

    const chunks = decoder.decode(value, { stream: true }).split('\n\n');
    console.debug("Received chunks:", chunks);
    const data = [];
    for (const x of chunks.filter(c => c !== '')) {
      const parsed = parseStreamChunk(x);
      if (parsed !== null) {
        data.push(parsed);
      }
    }

    yield data;
  }
}
