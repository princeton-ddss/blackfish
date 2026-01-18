import { blackfishApiURL } from "@/config";

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

  console.log("Starting completion stream with request:", JSON.parse(body));

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
    const error = new Error("Stream request failed.");
    error.status = res.status;
    throw error;
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
    const data = chunks.filter(x => x !== '').map((x) => {
      if (x === 'data: [DONE]') {
        // stream is done
        return {
          choices: [
            {
              delta: {
                content: "",
              }
            }
          ]
        }
      } else {
        return JSON.parse(x.replace('data: {', '{'));
      }
    });

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

  console.log("Starting text generation stream with request:", JSON.parse(body));

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
    const error = new Error("Stream request failed.");
    error.status = res.status;
    throw error;
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
export async function* streamChatCompletionInference(service, messages, params, use_proxy=false) {

  const body = JSON.stringify({
    messages: messages,
    ...params,
  });

  console.log("Starting chat completion stream with request:", JSON.parse(body));

  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/v1/chat/completions?streaming=${params.stream}`
    : `http://127.0.0.1:${service.port}/v1/chat/completions`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body,
  });

  if (!res.ok) {
    const error = new Error("Stream request failed.");
    error.status = res.status;
    throw error;
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
    const data = chunks.filter(x => x !== '').map((x) => {
      if (x === 'data: [DONE]') {
        // stream is done
        return {
          choices: [
            {
              delta: {
                content: "",
              }
            }
          ]
        }
      } else {
        return JSON.parse(x.replace('data: {', '{'));
      }
    });

    yield data;
  }
}
