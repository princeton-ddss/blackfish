import { useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/solid";
import Label from "@/components/inputs/Label";
import Slider from "@/components/inputs/Slider";
import TextField from "@/components/inputs/TextField";
import PropTypes from "prop-types";

function StopInput({ label, tooltip, parameters, setParameters }) {
  const [input, setInput] = useState("");

  const handleAdd = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const trimmed = input.trim();
      if (
        trimmed &&
        parameters.stop.length < 4 &&
        !parameters.stop.includes(trimmed)
      ) {
        setParameters((parameters) => {
          return {
            ...parameters,
            stop: [...parameters.stop, input],
          };
        });
        setInput("");
      }
    }
  };

  const handleRemove = (index) => {
    setParameters((parameters) => {
      return {
        ...parameters,
        stop: parameters.stop.filter((_, i) => i !== index),
      };
    });
  };

  return (
    <div className="sm:col-span-4">
      <div className="flex flex-row justify-start">
        <Label label={label} description={tooltip} />
      </div>

      <input
        type="text"
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => handleAdd(event)}
        className={`mt-1 block w-full border-1 border-gray-300 rounded-md shadow-sm py-1 px-2 focus:border-white focus:ring-2 focus:ring-blue-500 sm:text-sm`}
      />

      <div className="mt-1.5 flex flex-wrap gap-1">
        {parameters.stop.map((val, index) => (
          <div
            key={`${val}-${index}`}
            className="flex items-center bg-blue-500 text-white font-extralight sm:text-sm pl-3 pr-2 py-1 rounded-full"
          >
            <span>{val}</span>
            <button
              type="button"
              onClick={() => handleRemove(index)}
              className="ml-1 text-white font-light hover:text-blue-200"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

StopInput.propTypes = {
  label: PropTypes.string,
  tooltip: PropTypes.string,
  parameters: PropTypes.object,
  setParameters: PropTypes.func,
};

const defaultCompletionParameters = {
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
};

const defaultChatParameters = {
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
};

function TextGenerateParameterForm({
  mode,
  parameters,
  setParameters,
}) {
  const [seed, setSeed] = useState(parameters.seed ?? "");
  const [errors, setErrors] = useState({ seed: "" });

  const defaultParameters =
    mode.value === "completion"
      ? defaultCompletionParameters
      : defaultChatParameters;

  const handleSeedChange = (val) => {
    setSeed(val);
    const num = Number(val);
    const validSeed = val === "" || (Number.isInteger(num) && num >= 0);
    const error = validSeed ? "" : "Must be a positive integer.";

    setErrors((e) => ({ ...e, seed: error }));

    setParameters((prev) => ({
      ...prev,
      seed: validSeed ? (val === "" ? null : num) : null,
    }));
  };

  return (
    <div className="bg-white sm:rounded-md mt-2 grow">
      <div className="mt-4">
        <form>
          <div className="grid grid-cols-1 sm:grid-cols-1 gap-y-4">
            {/* max_tokens / max_completion_tokens */}
            {mode.value === "completion" ? (
              <Slider
                name="Max tokens"
                value={parameters.max_tokens}
                tooltip="The maximum number of tokens that can be generated in the completion.

  The token count of your prompt plus max_tokens cannot exceed the model's context length. "
                min={1}
                max={4096}
                onSliderChange={(event) => {
                  setParameters({
                    ...parameters,
                    max_tokens: Number(event.target.value),
                  });
                }}
                onTextChange={(event) => {
                  const value = Number(event.target.value);
                  if (value > 4096) {
                    // TODO: animation
                    console.warn("Maximum max_tokens is 4096!");
                    setParameters({ ...parameters, max_tokens: 4096 });
                  } else if (value < 1) {
                    // TODO: animation
                    console.warn("Minimum max_tokens is 1!");
                    setParameters({ ...parameters, max_tokens: 1 });
                  } else {
                    setParameters({
                      ...parameters,
                      max_tokens: Math.round(value),
                    });
                  }
                }}
                onReset={(event) => {
                  event.preventDefault();
                  setParameters({
                    ...parameters,
                    max_tokens: defaultParameters.max_tokens,
                  });
                }}
              />
            ) : (
              <Slider
                name="Max completion tokens"
                value={parameters.max_completion_tokens}
                tooltip="An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens."
                min={1}
                max={4096}
                onSliderChange={(event) => {
                  setParameters({
                    ...parameters,
                    max_completion_tokens: Number(event.target.value),
                  });
                }}
                onTextChange={(event) => {
                  const value = Number(event.target.value);
                  if (value > 4096) {
                    // TODO: animation
                    console.warn("Maximum max_completion_tokens is 4096!");
                    setParameters({
                      ...parameters,
                      max_completion_tokens: 4096,
                    });
                  } else if (value < 1) {
                    // TODO: animation
                    console.warn("Minimum max_completion_tokens is 1!");
                    setParameters({ ...parameters, max_completion_tokens: 1 });
                  } else {
                    setParameters({
                      ...parameters,
                      max_completion_tokens: Math.round(value),
                    });
                  }
                }}
                onReset={(event) => {
                  event.preventDefault();
                  setParameters({
                    ...parameters,
                    max_completion_tokens:
                      defaultParameters.max_completion_tokens,
                  });
                }}
              />
            )}

            {/* temperature */}
            <Slider
              name="Temperature"
              value={parameters.temperature}
              tooltip="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.

We generally recommend altering this or top_p but not both."
              min={0.0}
              max={2.0}
              step={0.01}
              onSliderChange={(event) => {
                const val = Number(event.target.value);
                setParameters({ ...parameters, temperature: val });
              }}
              onTextChange={(event) => {
                const value = Number(event.target.value);
                if (value > 2.0) {
                  // TODO: animation
                  console.warn("Maximum temperature is 2.0!");
                  setParameters({ ...parameters, temperature: 2.0 });
                } else if (value < 0.0) {
                  // TODO: animation
                  console.warn("Minimum temperature is 0.0!");
                  setParameters({ ...parameters, temperature: 0.0 });
                } else {
                  setParameters({ ...parameters, temperature: value });
                }
              }}
              onReset={(event) => {
                event.preventDefault();
                setParameters({
                  ...parameters,
                  temperature: defaultParameters.temperature,
                });
              }}
            />

            {/* frequency_penalty */}
            <Slider
              name="Frequency penalty"
              value={parameters.frequency_penalty}
              tooltip="Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim."
              min={-2.0}
              max={2.0}
              step={0.01}
              onSliderChange={(event) => {
                const val = Number(event.target.value);
                setParameters({ ...parameters, frequency_penalty: val });
              }}
              onTextChange={(event) => {
                const value = Number(event.target.value);
                if (value > 2.0) {
                  // TODO: animation
                  console.warn("Maximum frequency penalty is 2.0!");
                  setParameters({ ...parameters, frequency_penalty: 2.0 });
                } else if (value < -2.0) {
                  // TODO: animation
                  console.warn("Minimum frequency penalty is -2.0!");
                  setParameters({ ...parameters, frequency_penalty: -2.0 });
                } else {
                  setParameters({ ...parameters, frequency_penalty: value });
                }
              }}
              onReset={(event) => {
                event.preventDefault();
                setParameters({
                  ...parameters,
                  frequency_penalty: defaultParameters.frequency_penalty,
                });
              }}
            />

            {/* presence_penalty */}
            <Slider
              name="Presence penalty"
              value={parameters.presence_penalty}
              tooltip="Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics."
              min={-2.0}
              max={2.0}
              step={0.01}
              onSliderChange={(event) => {
                const val = Number(event.target.value);
                setParameters({ ...parameters, presence_penalty: val });
              }}
              onTextChange={(event) => {
                const value = Number(event.target.value);
                if (value > 2.0) {
                  // TODO: animation
                  console.warn("Maximum presence penalty is 2.0!");
                  setParameters({ ...parameters, presence_penalty: 2.0 });
                } else if (value < -2.0) {
                  // TODO: animation
                  console.warn("Minimum presence penalty is -2.0!");
                  setParameters({ ...parameters, presence_penalty: -2.0 });
                } else {
                  setParameters({ ...parameters, presence_penalty: value });
                }
              }}
              onReset={(event) => {
                event.preventDefault();
                setParameters({
                  ...parameters,
                  presence_penalty: defaultParameters.presence_penalty,
                });
              }}
            />

            {/* seed */}
            <TextField
              label="Seed"
              tooltip="If specified, our system will make a best effort to sample deterministically, such that repeated requests with the same seed and parameters should return the same result."
              value={seed}
              onChange={(e) => handleSeedChange(e.target.value)}
              placeholder=""
              error={errors.seed}
            />

            {/* stop */}
            <StopInput
              label="Stop sequences"
              tooltip="Up to 4 sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence."
              parameters={parameters}
              setParameters={setParameters}
            />
          </div>
        </form>
      </div>
    </div>
  );
}

TextGenerateParameterForm.propTypes = {
  mode: PropTypes.object,
  parameters: PropTypes.object,
  setParameters: PropTypes.func,
};

export default TextGenerateParameterForm;
