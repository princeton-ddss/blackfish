import { useEffect, useMemo, useState } from "react";
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from "@headlessui/react";
import {
  CheckIcon,
  ChevronUpDownIcon,
} from "@heroicons/react/20/solid";
import {
  CodeBracketIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";

import { Page } from "@/components/Page";
import { TaskContainer } from "@/components/TaskContainer";
import { SidebarContainer } from "@/components/SidebarContainer";

import TextGenerationCompletionContainer from "./components/TextGenerationCompletionContainer";
import TextGenerationChatContainer from "./components/TextGenerationChatContainer";
import TextGenerationContainerOptionsForm from "./components/TextGenerationContainerOptionsForm";
import TextGenerationParametersForm from "./components/TextGenerationParametersForm";
import CodeSnippetModal from "./components/CodeSnippetModal";

import PropTypes from "prop-types";

const modes = [
  { label: "Chat", value: "chat" },
  { label: "Completion (Legacy)", value: "completion" },
];

function ModeSelect({ selectedMode, setSelectedMode }) {
  return (
    <Listbox value={selectedMode} onChange={setSelectedMode}>
      <div className="relative">
        <ListboxButton className="relative cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-8 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 text-sm min-w-[120px]">
          <span className="block truncate">
            {selectedMode?.label || "Select task"}
          </span>
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
          </span>
        </ListboxButton>

        <ListboxOptions
          className="absolute z-10 mt-1 max-h-60 overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-sm shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none min-w-[120px]"
          anchor="bottom end"
        >
          {modes.map((mode) => (
            <ListboxOption
              key={mode.value}
              value={mode}
              className="group relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 dark:text-gray-100 data-[focus]:bg-blue-500 data-[focus]:text-white"
            >
              <span className="block truncate font-normal group-data-[selected]:font-semibold">
                {mode.label}
              </span>
              <span className="invisible group-data-[selected]:visible absolute inset-y-0 right-0 flex items-center pr-3 group-data-[focus]:text-white text-blue-600">
                <CheckIcon className="size-4" />
              </span>
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  );
}

ModeSelect.propTypes = {
  selectedMode: PropTypes.object,
  setSelectedMode: PropTypes.func,
};

export default function TextGenerationPage() {
  const [mode, setMode] = useState({
    label: "Chat",
    value: "chat",
    icon: null,
  });

  const [codeModalOpen, setCodeModalOpen] = useState(false);

  const [parameters, setParameters] = useState({
    // OpenAI API parameters
    // model: null,
    // best_of: null,
    // echo: false,
    frequency_penalty: 0.0,
    // logit_bias: null,
    // logprobs: null,
    max_tokens: 256,
    // n: 1,
    presence_penalty: 0.0,
    seed: null,
    stop: [],
    stream: true,
    temperature: 0.1,
    // top_p: null,

    // vLLM sampling parameters
    // use_beam_search: false,
    // top_k: null,
    // min_p: null,
    // repetition_penalty: null,
    // length_penalty: 1.0,
    // stop_token_ids: [],
    // include_stop_str_in_output: false,
    // ignore_eos: false,
    // min_tokens: 0,
    // skip_special_tokens: true,
    // spaces_between_special_tokens: true,
    // truncate_prompt_tokens: null,
    // allowed_token_ids: null,
    // prompt_logprobs: null,

    // vLLM extra parameters
    // add_special_tokens: false
    // response_format: "text",
    // guided_json: null,
    // guided_regex: null,
    // guided_choice: null,
    // guided_grammar: null,
    // guided_decoding_backend: null,
    // guided_whitespace_pattern: null,
    // priority: 0,
    // logits_processors: null,
    // return_tokens_as_token_ids: null,
    // kv_transfer_params: null,
  });

  const [chatParameters, setChatParameters] = useState({
    // OpenAI API parameters
    // model: null,
    // audio: null,
    frequency_penalty: 0.0,
    // function_call: null,
    // functions: null,
    // logit_bias: null,
    max_completion_tokens: 256,
    // max_tokens: null,
    // metadata: null,
    // modalities: ['text'],
    // n: 1,
    // parallel_tool_calls: true,
    // prediction: null,
    presence_penalty: 0.0,
    // reasoning_effort: null,
    // response_format: "text",
    seed: null,
    stop: [],
    // store: false,
    stream: true,
    temperature: 0.1,
    // tool_choice: null,
    // tools: null,
    // top_logprobs: null,
    // top_p: null,

    // vLLM sampling parameters
    // best_of: Optional[int] = None,
    // use_beam_search: false,
    // top_k: null,
    // min_p: null,
    // repetition_penalty: null,
    // length_penalty: 1.0,
    // stop_token_ids: [],
    // include_stop_str_in_output: false,
    // ignore_eos: false,
    // min_tokens: 0,
    // skip_special_tokens: true,
    // spaces_between_special_tokens: true,
    // truncate_prompt_tokens: null,
    // prompt_logprobs: null,

    // vLLM extra parameters
    // echo: false
    // add_generation_prompt: true
    // continue_final_message: false
    // add_special_tokens: false
    // documents: null,
    // chat_template: null,
    // chat_template_kwargs: null,
    // mm_processor_kwargs: null,
    // guided_json: null,
    // guided_regex: null,
    // guided_choice: null,
    // guided_grammar: null,
    // structural_tag: null,
    // guided_decoding_backend: null,
    // guided_whitespace_pattern: null,
    // priority: 0,
    // request_id: null,
    // logits_processors: null,
    // return_tokens_as_token_ids: null,
    // cache_salt: null,
    // kv_transfer_params: null,
  });

  const defaultContainerOptions = useMemo(() => {
    return {
      disable_custom_kernels: false,
    };
  }, []);

  // System message state (for Chat mode)
  const [systemMessage, setSystemMessage] = useState({
    role: "system",
    content: sessionStorage.getItem("tgcc-sm") || "",
  });

  const handleSystemMessageChange = (value) => {
    setSystemMessage((prev) => ({ ...prev, content: value }));
    sessionStorage.setItem("tgcc-sm", value);
  };

  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!isReady) return null;

  return (
    <Page task="text-generation">
      <TaskContainer>
        {mode.value === "completion" ? (
          <TextGenerationCompletionContainer
            parameters={parameters}
            toolbar={
              <div className="flex items-center">
                <button
                  type="button"
                  className="group relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 rounded-md"
                  aria-label="Code"
                  onClick={() => setCodeModalOpen(true)}
                >
                  <CodeBracketIcon className="h-5 w-5" />
                  <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">Code</span>
                </button>
                <button
                  type="button"
                  className="group relative p-2 mr-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 rounded-md"
                  aria-label="History"
                >
                  <ClockIcon className="h-5 w-5" />
                  <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">History</span>
                </button>
                <ModeSelect selectedMode={mode} setSelectedMode={setMode} />
              </div>
            }
          />
        ) : (
          <TextGenerationChatContainer
            parameters={chatParameters}
            systemMessage={systemMessage}
            toolbar={
              <div className="flex items-center">
                <button
                  type="button"
                  className="group relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 rounded-md"
                  aria-label="Code"
                  onClick={() => setCodeModalOpen(true)}
                >
                  <CodeBracketIcon className="h-5 w-5" />
                  <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">Code</span>
                </button>
                <button
                  type="button"
                  className="group relative p-2 mr-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 rounded-md"
                  aria-label="History"
                >
                  <ClockIcon className="h-5 w-5" />
                  <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">History</span>
                </button>
                <ModeSelect selectedMode={mode} setSelectedMode={setMode} />
              </div>
            }
          />
        )}
      </TaskContainer>

      <SidebarContainer
        task="text-generation"
        defaultContainerOptions={defaultContainerOptions}
        ContainerOptionsFormComponent={TextGenerationContainerOptionsForm}
        ParametersFormComponent={TextGenerationParametersForm}
        parametersFormProps={{
          mode,
          parameters: mode.value === "completion" ? parameters : chatParameters,
          setParameters: mode.value === "completion" ? setParameters : setChatParameters,
        }}
        systemMessage={mode.value === "chat" ? systemMessage : null}
        onSystemMessageChange={mode.value === "chat" ? handleSystemMessageChange : null}
      />

      <CodeSnippetModal
        open={codeModalOpen}
        onClose={() => setCodeModalOpen(false)}
        mode={mode.value}
        parameters={mode.value === "completion" ? parameters : chatParameters}
      />
    </Page>
  );
}
