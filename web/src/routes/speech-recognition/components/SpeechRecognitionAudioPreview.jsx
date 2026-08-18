import { blackfishApiURL } from "@/config";
import { isRemoteProfile } from "@/lib/util";
import PropTypes from "prop-types";

function SpeechRecognitionAudioPreview({ audioPath, profile = null }) {
  // Remote profiles stream the file over SFTP on the service's host; the
  // backend opens its own connection per request when `profile` is present.
  const profileParam = isRemoteProfile(profile)
    ? `&profile=${encodeURIComponent(profile.name)}`
    : "";

  return audioPath ? (
    <div className="w-full lg:w-5/6 max-w-6xl">
      <audio
        src={`${blackfishApiURL}/api/audio?path=${encodeURIComponent(audioPath)}${profileParam}`}
        title={`Preview ${audioPath}`}
        className="w-full mb-3 rounded-md"
        controls
      ></audio>
      <div className="w-full text-right font-extralight sm:text-xs mb-3 text-gray-600 dark:text-gray-400">
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
      <div className="w-full text-right font-extralight sm:text-xs mb-3 text-gray-600 dark:text-gray-400">
        No file selected
      </div>
    </div>
  );
}

SpeechRecognitionAudioPreview.propTypes = {
  audioPath: PropTypes.string,
  profile: PropTypes.object,
};

export default SpeechRecognitionAudioPreview;
