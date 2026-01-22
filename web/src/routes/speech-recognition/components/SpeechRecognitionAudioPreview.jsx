import { blackfishApiURL } from "@/config";
import PropTypes from "prop-types";

function SpeechRecognitionAudioPreview({ audioPath }) {
  return audioPath ? (
    <div className="w-full lg:w-5/6 max-w-6xl">
      <audio
        src={`${blackfishApiURL}/api/audio?path=${audioPath}`}
        title={`Preview ${audioPath}`}
        className="w-full mb-3 rounded-md"
        controls
      ></audio>
      <div className="w-full text-right font-extralight sm:text-xs mb-3">
        {audioPath}
      </div>
    </div>
  ) : (
    <div className="w-full lg:w-5/6 max-w-6xl">
      <audio
        src={""}
        title={"No file selected"}
        className="w-full mb-3 rounded-md"
        controls
      ></audio>
      <div className="w-full text-right font-extralight sm:text-xs mb-3">
        No file selected
      </div>
    </div>
  );
}

SpeechRecognitionAudioPreview.propTypes = {
  audioPath: PropTypes.string,
};

export default SpeechRecognitionAudioPreview;
