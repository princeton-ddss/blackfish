import { assetPath } from "@/config";
import PropTypes from "prop-types";

function SpeechRecognitionOutput({output, isLoading}) {
  if (!output && !isLoading) return <></>;
  return (
    <div className="h-52 w-full lg:w-5/6 max-w-6xl shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg mb-1 mt-4 overflow-y-scroll">
      <div className="h-full px-4 sm:px-6 lg:px-8">
        <div className="h-full py-6 flow-root">
          <div className="h-full overflow-x-auto sm:-mx-6 lg:-mx-8">
            <div className="h-full inline-block min-w-full py-2 align-middle">
              <div>
                {isLoading ? (
                  <div className="flex flex-row align-middle justify-center items-center">
                    <img
                      className="animate-bounce mt-10 h-16 w-auto"
                      height="64"
                      width="64"
                      src={assetPath("/img/orca.png")}
                      alt="blackfish"
                    />
                  </div>
                ) : (
                  <textarea
                    name="output"
                    id="output"
                    className="h-36 block w-full resize-none border-0 border-b border-transparent p-0 pb-2 text-gray-600 placeholder:text-gray-400 focus:border-0 focus:ring-0 sm:text-sm sm:leading-6 px-6"
                    value={output}
                    disabled={output === ""}
                    placeholder='Select a file and click "Submit" to transcribe it.'
                    onChange={() => null}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

SpeechRecognitionOutput.propTypes = {
  output: PropTypes.string,
  isLoading: PropTypes.bool,
};

export default SpeechRecognitionOutput;
