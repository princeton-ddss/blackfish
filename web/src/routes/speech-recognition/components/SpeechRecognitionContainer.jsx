import { useState, useContext, useRef, useEffect } from "react";
import AudioFileBrowser from "@/components/AudioFileBrowser";
import Notification from "@/components/Notification";
import SpeechRecognitionAudioPreview from "./SpeechRecognitionAudioPreview";
import SpeechRecognitionOutput from "./SpeechRecognitionOutput";
import SpeechRecognitionSubmit from "./SpeechRecognitionSubmit";
import { callSpeechRecognitionInference } from "../lib/requests";
import { ServiceContext } from "@/providers/ServiceProvider";
import PropTypes from "prop-types";


function SpeechRecognitionContainer({
  parameters,
}) {

  const [audioPath, setAudioPath] = useState("");
  const [output, setOutput] = useState("");
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const { selectedService, registerInFlight } = useContext(ServiceContext);
  // Tracks the in-flight transcription so it can be cancelled by the user or on
  // unmount. Stop/Delete cancellation goes through the ServiceProvider registry
  // (keyed by the request's service), so it targets the right request even if a
  // different service is selected while this one is still running.
  const abortRef = useRef(null);

  const handleSubmit = async () => {
    if (!selectedService) return;
    const service = selectedService; // bind to the service this request runs against
    const controller = new AbortController();
    abortRef.current = controller;
    // Register under this service's id so a Stop/Delete on it aborts the request.
    const unregister = registerInFlight(service.id, () => controller.abort());
    setIsLoading(true);
    setError(null);
    try {
      const res = await callSpeechRecognitionInference(
        service,
        audioPath,
        parameters,
        true,
        controller.signal,
      );
      setOutput(res.text.trim());
    } catch (err) {
      // A cancelled request is expected — leave the output untouched. Surface a
      // real failure (network error, service returned an error) to the user.
      if (err.name !== "AbortError") {
        console.error("Transcription error:", err);
        setError({
          message: "Transcription failed",
          detail: err.message || "The service may be unavailable.",
        });
      }
    } finally {
      unregister();
      if (abortRef.current === controller) abortRef.current = null;
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
  };

  // Cancel an in-flight request when leaving the page.
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const getFileBrowserStatus = () => {

    if (!selectedService) {
      return {
        disabled: true,
        detail: "No service selected."
      };
    } else if (!selectedService.mount) {
      return {
        disabled: true,
        detail: "Oops! This service doesn't seem to have a mount directory."
      };
    }

    if (selectedService.host === "localhost") {
      return {
        disabled: false,
      };
    } else {
      return {
        disabled: true,
        detail: "Remote file access isn't supported for this version of Blackfish."
      };
    }
  };

  const fileBrowserStatus = getFileBrowserStatus();

  return (
    <div className="bg-white dark:bg-gray-800">
      <div className="relative w-full lg:w-5/6 max-w-6xl">
        <AudioFileBrowser
          root={selectedService ? selectedService.mount : ""}
          setAudioPath={setAudioPath}
          status={fileBrowserStatus}
        />
        <div className="absolute bottom-0 py-2 px-5 bg-gray-50 dark:bg-gray-800 w-full max-w-6xl rounded-es-md rounded-ee-md">
          <SpeechRecognitionSubmit
            selectedService={selectedService}
            audioPath={audioPath}
            isLoading={isLoading}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
          />
        </div>
      </div>
      <SpeechRecognitionAudioPreview
        audioPath={audioPath}
      />
      <SpeechRecognitionOutput
        output={output}
        isLoading={isLoading}
      />
      <Notification
        show={!!error}
        variant="error"
        message={error ? error.message : ""}
        detail={error ? error.detail : ""}
        onDismiss={() => setError(null)}
      />
    </div>
  );
}

SpeechRecognitionContainer.propTypes = {
  parameters: PropTypes.object,
};

export default SpeechRecognitionContainer;
