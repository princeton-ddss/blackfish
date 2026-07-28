import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import SpeechRecognitionSubmit from "./SpeechRecognitionSubmit";
import { ServiceStatus } from "@/lib/util";

const healthyService = { name: "svc", status: ServiceStatus.HEALTHY };

describe("SpeechRecognitionSubmit", () => {
  test("submits when idle, healthy, and an audio path is set", async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const { getByRole } = render(
      <SpeechRecognitionSubmit
        selectedService={healthyService}
        audioPath="/a/clip.wav"
        isLoading={false}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );
    await act(async () => {
      await userEvent.click(getByRole("button"));
    });
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onCancel).not.toHaveBeenCalled();
  });

  test("cancels (not submits) while a request is in flight", async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const { getByRole } = render(
      <SpeechRecognitionSubmit
        selectedService={healthyService}
        audioPath="/a/clip.wav"
        isLoading={true}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );
    const button = getByRole("button");
    // The cancel button is never disabled, so it can always be pressed.
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("aria-label", "Cancel transcription");
    await act(async () => {
      await userEvent.click(button);
    });
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("submit is disabled when idle without a healthy service or audio path", () => {
    const { getByRole, rerender } = render(
      <SpeechRecognitionSubmit
        selectedService={healthyService}
        audioPath=""
        isLoading={false}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(getByRole("button")).toBeDisabled(); // no audio path

    rerender(
      <SpeechRecognitionSubmit
        selectedService={{ name: "svc", status: ServiceStatus.STOPPED }}
        audioPath="/a/clip.wav"
        isLoading={false}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(getByRole("button")).toBeDisabled(); // not healthy
  });
});
