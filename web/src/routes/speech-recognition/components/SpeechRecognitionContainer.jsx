import { useState, useContext } from "react";
import AudioFileBrowser from "@/components/AudioFileBrowser";
import SpeechRecognitionAudioPreview from "./SpeechRecognitionAudioPreview";
import SpeechRecognitionOutput from "./SpeechRecognitionOutput";
import SpeechRecognitionSubmit from "./SpeechRecognitionSubmit";
import { ServiceContext } from "@/providers/ServiceProvider";
import PropTypes from "prop-types";


function SpeechRecognitionContainer({
  parameters,
}) {

  const [audioPath, setAudioPath] = useState("");
  const [output, setOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { selectedService } = useContext(ServiceContext);

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
    <div className="pt-2 bg-white">
      <div className="relative w-full lg:w-5/6 max-w-6xl">
        <AudioFileBrowser
          root={selectedService ? selectedService.mount : ""}
          setAudioPath={setAudioPath}
          status={fileBrowserStatus}
        />
        <div className="absolute bottom-0 py-2 px-5 bg-gray-50 w-full max-w-6xl rounded-es-md rounded-ee-md">
          <SpeechRecognitionSubmit
            selectedService={selectedService}
            audioPath={audioPath}
            setOutput={setOutput}
            parameters={parameters}
            setIsLoading={setIsLoading}
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
