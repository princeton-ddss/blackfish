/* eslint react/prop-types: 0 */

import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { ServiceContext } from "@/providers/ServiceProvider";
import { ServiceStatus } from "@/lib/util";
import { callSpeechRecognitionInference } from "../lib/requests";
import SpeechRecognitionContainer from "./SpeechRecognitionContainer";

vi.mock("../lib/requests", () => ({
  callSpeechRecognitionInference: vi.fn(),
}));

// File-system browsing needs its own providers; keep the real submit and output.
vi.mock("@/components/AudioFileBrowser", () => ({
  default: function MockAudioFileBrowser({ children, setAudioPath }) {
    return (
      <div>
        <button onClick={() => setAudioPath("/audio/clip.wav")}>Select clip</button>
        {children}
      </div>
    );
  },
}));

test("keeps the previous transcript when a cancelled request resolves successfully", async () => {
  const user = userEvent.setup();
  const service = {
    id: "speech-service",
    name: "Speech service",
    status: ServiceStatus.HEALTHY,
    host: "localhost",
    mount: "/audio",
  };
  const unregister = vi.fn();
  const registerInFlight = vi.fn(() => unregister);
  let resolveLateResult;
  const lateResult = new Promise((resolve) => {
    resolveLateResult = resolve;
  });
  callSpeechRecognitionInference
    .mockReset()
    .mockResolvedValueOnce({ text: "Original transcript" })
    .mockReturnValueOnce(lateResult);

  render(
    <ServiceContext.Provider value={{ selectedService: service, registerInFlight }}>
      <SpeechRecognitionContainer parameters={{}} />
    </ServiceContext.Provider>,
  );

  await user.click(screen.getByRole("button", { name: "Select clip" }));
  await user.click(screen.getByRole("button", { name: "Submit to Speech service" }));
  expect(await screen.findByDisplayValue("Original transcript")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Submit to Speech service" }));
  expect(callSpeechRecognitionInference).toHaveBeenCalledTimes(2);
  const signal = callSpeechRecognitionInference.mock.calls[1][4];
  expect(signal.aborted).toBe(false);
  await user.click(screen.getByRole("button", { name: "Cancel transcription" }));
  expect(signal.aborted).toBe(true);

  // Deliberately resolve despite abort(), reproducing a late upstream response.
  await act(async () => {
    resolveLateResult({ text: "Cancelled request's late transcript" });
    await lateResult;
  });

  expect(screen.getByRole("textbox")).toHaveValue("Original transcript");
  expect(screen.getByRole("button", { name: "Submit to Speech service" })).toBeEnabled();
  expect(unregister).toHaveBeenCalledTimes(2);
});
