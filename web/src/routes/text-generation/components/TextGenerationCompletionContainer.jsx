import React, { useContext } from "react";
import { ServiceContext } from "@/providers/ServiceProvider";
import { streamCompletionInference } from "../lib/requests";
import {
  ArrowPathIcon,
  ClipboardDocumentIcon,
  PaperAirplaneIcon,
  PaperClipIcon,
}
from "@heroicons/react/24/outline";

import { ServiceStatus } from "@/lib/util";
import PropTypes from "prop-types";


/**
 * Text generation prompt input component.
 * @param {object} options
 * @param {string} options.prompt
 * @param {Function} options.setPrompt
 * @param {Function} options.handleSubmit
 * @param {object} options.selectedService
 * @param {boolean} options.isLoading
 * @return {JSX.Element}
 */
function TextGenerationPromptInput({
  prompt,
  setPrompt,
  handleSubmit,
  selectedService,
  toolbar,
}) {
  /**
   * Set input value in React state and session storage.
   * @param {string} value
   */
  function handleChange(value) {
    setPrompt(value || "");
    sessionStorage.setItem("tgci", value || "");
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100">
          Prompt
        </label>
        {toolbar}
      </div>

      {/* TODO: disable while isLoading... */}

      <div className="flex items-start space-x-4">
        <div className="min-w-0 flex-1">
          <form action="#" onSubmit={handleSubmit} className="relative">
            <div className="rounded-lg bg-white dark:bg-gray-700 outline outline-1 -outline-offset-1 outline-gray-300 dark:outline-gray-600 shadow-md">
              <label htmlFor="text-generation-text-input" className="sr-only">
                Prompt anything
              </label>
              <textarea
                id="text-generation-text-input"
                name="text-generation-text-input"
                rows={10}
                placeholder="Orcas are awesome because..."
                value={prompt}
                onChange={(event) => handleChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && event.shiftKey) {
                    // Allow new line
                    return;
                  } else if (event.key === "Enter") {
                    event.preventDefault();
                    handleSubmit(event);
                  }
                }}
                className="block w-full resize-none bg-transparent px-4 py-3 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 border-0  focus:border-0 focus:outline-none focus:ring-0 sm:text-sm/6 overflow-visible"
              />

              {/* Spacer element to match the height of the toolbar */}
              <div aria-hidden="true" className="py-2">
                {/* Matches height of button in toolbar (1px border + 36px content height) */}
                <div className="py-px">
                  <div className="h-9" />
                </div>
              </div>
            </div>

            <div className="absolute inset-x-0 bottom-0 flex justify-between py-2 pl-3 pr-2">
              <div className="flex items-center space-x-5">
                <div className="flex items-center">
                  <button
                    type="button"
                    className="-m-2.5 flex size-10 items-center justify-center rounded-full text-gray-400 hover:text-gray-500"
                  >
                    <PaperClipIcon aria-hidden="true" className="size-5" />
                    <span className="sr-only">Attach a file</span>
                  </button>
                </div>
              </div>
              <div className="shrink-0">
                <button
                  type="submit"
                  disabled={!selectedService || selectedService.status !== ServiceStatus.HEALTHY}
                  onClick={() => {
                    console.log("Submit button clicked:", prompt);
                  }}
                  className="inline-flex items-center rounded-full bg-white dark:bg-gray-600 p-2 text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-500 shadow-sm hover:bg-gray-100 dark:hover:bg-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 disabled:opacity-50 disabled:hover:bg-white dark:disabled:hover:bg-gray-600 disabled:border-gray-200 dark:disabled:border-gray-600 disabled:shadow-none"
                >
                  <PaperAirplaneIcon className="size-5" />
                </button>


                {/* <button
                    type="submit"
                    disabled={!selectedService || selectedService.status !== ServiceStatus.HEALTHY}
                    className="relative disabled:text-gray-400 -ml-px inline-flex items-center gap-x-1.5 rounded-md px-3 py-2 text-sm font-medium text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                  >
                    <PaperAirplaneIcon className="-ml-0.5 h-5 w-5" aria-hidden="true" />
                    {selectedService ? `Submit to ${selectedService.name}` : "Submit"}
                  </button> */}
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

TextGenerationPromptInput.propTypes = {
  prompt: PropTypes.string,
  setPrompt: PropTypes.func,
  handleSubmit: PropTypes.func,
  selectedService: PropTypes.object,
  isLoading: PropTypes.bool
};

/**
 * Text generation response output component.
 * @param {object} options
 * @param {string} options.content
 * @param {Function} options.handleSubmit
 * @param {object} options.selectedService
 * @param {boolean} options.isLoading
 * @return {JSX.Element}
 */
function TextGenerationResponseOutput({
  content,
  handleSubmit,
  selectedService,
}) {
  if (content && content.length > 0) {
    try {
      sessionStorage.setItem("tgco", content);
    } catch(error) {
      console.error(error);
    };
    return (
      <div>
        {/* TODO: display loading in case first token is slow... */}
        <div className="mt-8">
          <div className="block w-full max-w-4xl overflow-y-auto bg-white dark:bg-transparent text-sm/6 text-gray-900 dark:text-gray-100 rounded-lg ml-1">
            {content}
          </div>
        </div>
        <div className="flex flex-row h-8 mt-1">
          <button
            onClick={() => {
              navigator.clipboard
                .writeText(content)
                .then(console.log("copied assistant message"))
                .catch((err) => {
                  console.error("Failed to copy content: ", err);
                });
            }}
          >
            <ClipboardDocumentIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5" />
          </button>
          <button
            disabled={!selectedService || selectedService.status !== ServiceStatus.HEALTHY}
            onClick={handleSubmit}
          >
            <ArrowPathIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5" />
          </button>
        </div>
      </div>
    );
  }
}

TextGenerationResponseOutput.propTypes = {
  content: PropTypes.string,
  handleSubmit: PropTypes.func,
  selectedService: PropTypes.object,
  isLoading: PropTypes.bool
};

/**
 * Text generation completion container component.
 * @param {object} options
 * @param {object} options.parameters
 * @param {JSX.Element} options.toolbar
 * @return {JSX.Element}
 */
function TextGenerationCompletionContainer({ parameters, toolbar }) {
  const { selectedService } = useContext(ServiceContext);
  const [prompt, setPrompt] = React.useState(
    sessionStorage.getItem("tgci") || ""
  );
  const [response, setResponse] = React.useState(
    sessionStorage.getItem("tgco") || ""
  );
  const [isLoading, setIsLoading] = React.useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const inputs = prompt === "" ? "Write me a haiku about orcas." : prompt;

    setIsLoading(true);
    setResponse("");
    sessionStorage.setItem("tgco", "");

    const stream = streamCompletionInference(
      selectedService,
      inputs,
      {
        ...parameters,
        stream: true,
      },
      true
    );


    const data = await stream.next();
    setIsLoading(false);
    const text = data.value
      .map((x) => x.choices[0].text)
      .join("")
      .trimStart();
    setResponse((prevResponse) => prevResponse + text);

    for await (const data of stream) {
      const text = data.map((x) => x.choices[0].text).join("");
      setResponse((prevOutput) => prevOutput + text);
    }
  };

  return (
    <div className="flex flex-col grow pt-2 bg-white dark:bg-gray-800">
      <TextGenerationPromptInput
        prompt={prompt || ""}
        setPrompt={setPrompt}
        handleSubmit={handleSubmit}
        selectedService={selectedService}
        isLoading={isLoading}
        toolbar={toolbar}
      />
      <TextGenerationResponseOutput
        content={response || ""}
        handleSubmit={handleSubmit}
        selectedService={selectedService}
        isLoading={isLoading}
      />
    </div>
  );
}

TextGenerationCompletionContainer.propTypes = {
  parameters: PropTypes.object,
  toolbar: PropTypes.node,
};

export default TextGenerationCompletionContainer;
