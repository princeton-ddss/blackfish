import { blackfishApiURL } from "@/config";

/** Call a service with given ID. Pass `signal` to allow cancellation. */
export async function callSpeechRecognitionInference(service, audioPath, params, use_proxy=false, signal=undefined) {
  const url = use_proxy
    ? `${blackfishApiURL}/proxy/${service.port}/transcribe`
    : `http://127.0.0.1:${service.port}/transcribe`

  const body = {
    audio_path: audioPath.replace(service.mount, "/data/audio"),
    response_format: "text",
    language: params.language.name.toLowerCase(),
  }
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    mode: "cors",
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    // Preserve the backend's status and message so callers can distinguish a
    // timeout (504) from other failures and show an actionable message.
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      // Response had no JSON body; fall back to a generic message below.
    }
    const err = new Error(detail || "Failed to call the service");
    err.status = res.status;
    throw err;
  }

  return res.json();
}
