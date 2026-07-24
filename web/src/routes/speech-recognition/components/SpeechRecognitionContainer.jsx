import { useState, useContext, useRef, useEffect } from "react";
import AudioFileBrowser from "@/components/AudioFileBrowser";
import SpeechRecognitionAudioPreview from "./SpeechRecognitionAudioPreview";
import SpeechRecognitionOutput from "./SpeechRecognitionOutput";
import SpeechRecognitionSubmit from "./SpeechRecognitionSubmit";
import { callSpeechRecognitionInference } from "../lib/requests";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ServiceStatus } from "@/lib/util";
import PropTypes from "prop-types";


function SpeechRecognitionContainer({
  parameters,
}) {

  const [audioPath, setAudioPath] = useState("");
  const [output, setOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { selectedService, registerInFlight } = useContext(ServiceContext);
  // Tracks the in-flight transcription so it can be cancelled (by the user, by
  // a service action like Stop, or on unmount).
  const abortRef = useRef(null);

  const handleSubmit = async () => {
    if (!selectedService) return;
    const controller = new AbortController();
    abortRef.current = controller;
    // Register so a Stop/Delete on this service aborts the request immediately.
    const unregister = registerInFlight(() => controller.abort());
    setIsLoading(true);
    try {
      const res = await callSpeechRecognitionInference(
        selectedService,
        audioPath,
        parameters,
        true,
        controller.signal,
      );
      setOutput(res.text.trim());
    } catch (err) {
      // A cancelled request is expected — leave the output untouched.
      if (err.name !== "AbortError") throw err;
    } finally {
      unregister();
      if (abortRef.current === controller) abortRef.current = null;
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
  };

  // Also cancel if the service leaves the healthy state by any other path
  // (e.g. it crashes), and on unmount.
  useEffect(() => {
    if (selectedService?.status !== ServiceStatus.HEALTHY) {
      abortRef.current?.abort();
    }
  }, [selectedService?.status]);

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
    </div>
  );
}

SpeechRecognitionContainer.propTypes = {
  parameters: PropTypes.object,
};

export default SpeechRecognitionContainer;
