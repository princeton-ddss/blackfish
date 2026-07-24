import { PaperAirplaneIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { ServiceStatus } from "@/lib/util";
import PropTypes from "prop-types";


function SpeechRecognitionSubmit({
  selectedService,
  audioPath,
  isLoading,
  onSubmit,
  onCancel,
}) {

  const handleClick = (event) => {
    event.preventDefault();
    if (isLoading) {
      onCancel();
    } else if (selectedService) {
      onSubmit();
    } else {
      console.warn("submit clicked with no service provided");
    }
  };

  // While a request is in flight the button cancels (never disabled, so it can
  // always be pressed). Otherwise it submits and follows the usual guards.
  const submitDisabled =
    audioPath === "" ||
    !selectedService ||
    selectedService.status !== ServiceStatus.HEALTHY;

  return (
    <form onSubmit={handleClick} className="flex justify-end">
      <button
        type="submit"
        disabled={!isLoading && submitDisabled}
        className="inline-flex items-center rounded-full bg-white dark:bg-gray-700 p-2 text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 shadow-sm hover:bg-gray-100 dark:hover:bg-gray-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 dark:disabled:text-gray-500 disabled:opacity-50 disabled:hover:bg-white dark:disabled:hover:bg-gray-700 disabled:border-gray-200 dark:disabled:border-gray-600 disabled:shadow-none"
        aria-label={
          isLoading
            ? "Cancel transcription"
            : selectedService
              ? `Submit to ${selectedService.name}`
              : "Submit"
        }
      >
        {isLoading ? (
          <XMarkIcon className="size-5" aria-hidden="true" />
        ) : (
          <PaperAirplaneIcon className="size-5" aria-hidden="true" />
        )}
      </button>
    </form>
  );
}

SpeechRecognitionSubmit.propTypes = {
  selectedService: PropTypes.object,
  audioPath: PropTypes.string,
  isLoading: PropTypes.bool,
  onSubmit: PropTypes.func,
  onCancel: PropTypes.func,
};

export default SpeechRecognitionSubmit;
