import { PaperAirplaneIcon } from "@heroicons/react/24/outline";
import { callSpeechRecognitionInference } from "../lib/requests";
import { ServiceStatus } from "@/lib/util";
import PropTypes from "prop-types";


function SpeechRecognitionSubmit({
  selectedService,
  audioPath,
  setOutput,
  parameters,
  setIsLoading,
}) {

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (selectedService) {
      setIsLoading(true);
      const res = await callSpeechRecognitionInference(
        selectedService,
        audioPath,
        parameters,
        true
      );
      setIsLoading(false);
      setOutput(res.text.trim());
    } else {
      console.warn("handleSubmit called with no service provided")
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex justify-end">
      <button
        type="submit"
        disabled={audioPath === "" || !selectedService || selectedService.status !== ServiceStatus.HEALTHY}
        className="inline-flex items-center rounded-full bg-white p-2 text-sm font-semibold text-gray-900 border border-gray-300 shadow-sm hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 disabled:opacity-50 disabled:hover:bg-white disabled:border-gray-200 disabled:shadow-none"
        aria-label={selectedService ? `Submit to ${selectedService.name}` : "Submit"}
      >
        <PaperAirplaneIcon className="size-5" aria-hidden="true" />
      </button>
    </form>
  );
}

SpeechRecognitionSubmit.propTypes = {
  selectedService: PropTypes.object,
  audioPath: PropTypes.string,
  setOutput: PropTypes.func,
  parameters: PropTypes.object,
  setIsLoading: PropTypes.func,
};

export default SpeechRecognitionSubmit;
