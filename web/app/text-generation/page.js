"use client";

import { useEffect, useMemo, useState } from "react";
import { Label, Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon, ExclamationTriangleIcon } from "@heroicons/react/20/solid";

import { Page } from "../components/Page";
import { TaskContainer } from "../components/TaskContainer";
import { SidebarContainer } from "../components/SidebarContainer";

import TextGenerationCompletionContainer from "./components/TextGenerationCompletionContainer";
import TextGenerationChatContainer from "./components/TextGenerationChatContainer";
import TextGenerationContainerOptionsForm from "./components/TextGenerationContainerOptionsForm";
import TextGenerationParametersForm from "./components/TextGenerationParametersForm";

import PropTypes from "prop-types";

function ModeSelect({ selectedMode, setSelectedMode }) {

  // eslint-disable-next-line no-unused-vars
  const [modes, setModes] = useState([
    {
      label: "Completion",
      value: "completion",
      icon: null,
    },
    {
      label: "Chat",
      value: "chat",
      icon: null,
    },
  ]);

  return (
    <Listbox value={selectedMode} onChange={setSelectedMode}>

      <Label className="block text-sm font-medium leading-6 text-gray-900">
        Task
      </Label>

      <div className="relative mt-2 mb-2 w-64">
        {
          selectedMode
            ? <ListboxButton
              className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 sm:text-sm sm:leading-6"
            >
              <span className="flex items-center">
                <span className="ml-3 block truncate">
                  {selectedMode.label ? selectedMode.label : ""}
                </span>

                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                  <ChevronUpDownIcon
                    className="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </span>
              </span>
            </ListboxButton>
            : <ListboxButton
              className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 sm:text-sm sm:leading-6"
            >
              <span className="flex items-center">
                <span className="pointer-events-none flex-shrink-0 pl-3">
                  <ExclamationTriangleIcon
                    className="h-5 w-5 text-yellow-400"
                    aria-hidden="true"
                  />
                </span>
                <span className="ml-3 block truncate">
                  {"No profile selected"}
                </span>
                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                  <ChevronUpDownIcon
                    className="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </span>
              </span>
            </ListboxButton>
        }

        <ListboxOptions
          className="absolute z-10 mt-1 max-h-60 overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm w-[var(--button-width)]"
          anchor="bottom"
        >
          {modes.map((mode) => (
            <ListboxOption
              key={mode.value}
              value={mode}
              className="group flex gap-2 bg-white data-[focus]:bg-blue-500 data-[focus]:text-white relative cursor-default select-none py-2 pl-1 pr-9 text-gray-900"
            >
              <div className="flex">
                <span className="ml-3 block truncate font-normal data-[selected]:font-semibold">
                  {mode.label}
                </span>
              </div>
              <span className="invisible group-data-[selected]:visible absolute inset-y-0 right-0 flex items-center pr-4 group-data-[focus]:text-white text-blue-600">
                <CheckIcon className="size-5" />
              </span>
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  )
}

ModeSelect.propTypes = {
  selectedMode: PropTypes.object,
  setSelectedMode: PropTypes.func,
};

export default function TextGenerationPage() {

  const [mode, setMode] = useState({
    label: "Completion",
    value: "completion",
    icon: null,
  });

  const [parameters, setParameters] = useState({
    // OpenAI API parameters
    // model: null,
    // best_of: null,
    // echo: false,
    frequency_penalty: 0.0,
    // logit_bias: null,
    // logprobs: null,
    max_tokens: 16,
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
    max_completion_tokens: 16,
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
    }
  }, [])

  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!isReady) return null;

  return (
    <Page task="text-generation">
      <TaskContainer>
        <ModeSelect selectedMode={mode} setSelectedMode={setMode} />
        {
          mode.value === 'completion'
            ?
            <TextGenerationCompletionContainer parameters={parameters} />
            :
            <TextGenerationChatContainer parameters={chatParameters} />
        }
      </TaskContainer>

      <SidebarContainer
        task="text-generation"
        defaultContainerOptions={defaultContainerOptions}
        ContainerOptionsFormComponent={TextGenerationContainerOptionsForm}
      >
        <TextGenerationParametersForm
          mode={mode}
          parameters={mode.value === 'completion' ? parameters : chatParameters}
          setParameters={mode.value === 'completion' ? setParameters : setChatParameters}
        />
      </SidebarContainer>
    </Page>
  );
}
