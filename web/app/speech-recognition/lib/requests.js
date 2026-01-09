import { blackfishApiURL } from "../../config";

/** Call a service with given ID. */
export async function callSpeechRecognitionInference(service, audioPath, params, use_proxy=false) {
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
  });
  if (!res.ok) {
    throw new Error("Failed to call the service"); // activate the closest `error.js` Error Boundary
  }

  return res.json();
}
