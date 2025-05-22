import requests
from typing import Annotated, Any, Optional, Union
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field


from app.services.base import Service, BaseConfig
from app.logger import logger


@dataclass
class TextGenerationConfig(BaseConfig):
    # Required?
    model_dir: Optional[str] = None
    revision: Optional[str] = None

    # Core
    # model
    # host
    # port
    # api_key

    # Extras
    # uvicorn_log_level # {debug,info,warning,error,critical,trace}
    # disable_uvicorn_access_log
    # allow_credentials
    # allowed_origins
    # allowed_methods
    # allowed_headers
    # lora_modules
    # prompt_adapters
    # chat_template
    # chat_template_content_format # auto,string,openai
    # response_role
    # ssl_keyfile
    # ssl_certfile
    # ssl_ca_certs
    # enable_ssl_refresh
    # ssl_cert_reqs
    # root_path
    # middleware
    # return_tokens_as_token_ids
    # disable_frontend_multiprocessing
    # enable_request_id_headers
    # enable_auto_tool_choice
    # tool_call_parser # granite-20b-fc,granite,hermes,internlm,jamba,llama3_json,mistral,phi4_mini_json,pythonic or name registered in --tool-parser-plugin
    # tool_parser_plugin
    # task # auto,generate,embedding,embed,classify,score,reward,transcription
    # tokenizer
    # hf_config_path
    # skip_tokenizer_init
    # code_revision
    # tokenizer_revision
    # tokenizer_mode # {auto,slow,mistral,custom}
    # trust_remote_code
    # allowed_local_media_path
    # load_format # {auto,pt,safetensors,npcache,dummy,tensorizer,sharded_state,gguf,bitsandbytes,mistral,runai_streamer,fastsafetensors}
    # download_dir
    # model_loader_extra_config
    # use_tqdm_on_load # --no-use-tqdm-on-load
    # config_format # {auto,hf,mistral}
    # dtype # {auto,half,float16,bfloat16,float,float32}
    # kv_cache_dtype # {auto,fp8,fp8_e5m2,fp8_e4m3}
    # max_model_len
    # guided_decoding_backend
    # logits_processor_pattern
    # model_impl # {auto,vllm,transformers}
    # distributed_executor_backend # {ray,mp,uni,external_launcher}
    # pipeline_parallel_size
    # tensor_parallel_size
    # data_parallel_size
    # enable_expert_parallel # --no-enable-expert-parallel
    # max_parallel_loading_workers
    # ray_workers_use_nsight # --no-ray-workers-use-nsight
    # disable_custom_all_reduce # --no-disable-custom-all-reduce
    # block_size # {8,16,32,64,128}
    # enable_prefix_caching # --no-enable-prefix-caching
    # prefix_caching_hash_algo # {builtin,sha256}
    # disable_sliding_window
    # use_v2_block_manager
    # seed
    # swap_space
    # cpu_offload_gb
    # gpu_memory_utilization
    # num_gpu_blocks_override
    # max_logprobs
    # disable_log_stats
    # quantization # {aqlm,awq,deepspeedfp,tpu_int8,fp8,ptpc_fp8,fbgemm_fp8,modelopt,nvfp4,marlin,gguf,gptq_marlin_24,gptq_marlin,awq_marlin,gptq,compressed-tensors,bitsandbytes,qqq,hqq,experts_int8,neuron_quant,ipex,quark,moe_wna16,torchao,None}
    # rope_scaling
    # rope_theta
    # hf_token
    # hf_overrides
    # enforce_eager
    # max_seq_len_to_capture
    # tokenizer_pool_size
    # tokenizer_pool_type
    # tokenizer_pool_extra_config
    # limit_mm_per_prompt
    # mm_processor_kwargs
    # disable_mm_preprocessor_cache
    # enable_lora
    # enable_lora_bias
    # max_loras
    # max_lora_rank
    # lora_extra_vocab_size
    # lora_dtype # {auto,float16,bfloat16}
    # long_lora_scaling_factors
    # max_cpu_loras
    # fully_sharded_loras
    # enable_prompt_adapter
    # max_prompt_adapters
    # max_prompt_adapter_token
    # device # {auto,cuda,neuron,cpu,tpu,xpu,hpu}
    # num_scheduler_steps
    # speculative_config
    # ignore_patterns
    # preemption_mode
    # served_model_name
    # qlora_adapter_name_or_path
    # show_hidden_metrics_for_version
    # otlp_traces_endpoint
    # collect_detailed_traces
    # disable_async_output_proc
    # max_num_batched_tokens
    # max_num_seqs
    # max_num_partial_prefills
    # max_long_partial_prefills
    # long_prefill_token_threshold
    # num_lookahead_slots
    # scheduler_delay_factor
    # enable_chunked_prefill # --no-enable-chunked-prefill
    # multi_step_stream_outputs # --no-multi-step-stream-outputs
    # scheduling_policy # {fcfs,priority}
    # disable_chunked_mm_input # --no-disable-chunked-mm-input
    # scheduler_cls
    # override_neuron_config
    # override_pooler_config
    # compilation_config
    # kv_transfer_config
    # worker_cls
    # worker_extension_cls
    # generation_config
    # override_generation_config
    # enable_sleep_mode
    # calculate_kv_scales
    # additional_config
    # enable_reasoning
    # reasoning_parser # {deepseek_r1,granite}
    # disable_cascade_attn
    # disable_log_requests
    # max_log_len
    # disable_fastapi_docs
    # enable_prompt_tokens_details
    # enable_server_load_tracking

    launch_kwargs: Optional[str] = None


@dataclass
class TextGenerationParameters:
    """See https://platform.openai.com/docs/api-reference/chat and https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#chat-api."""

    # OpenAI Core
    audio: Optional[object] = None
    frequency_penalty: Optional[str] = None
    logit_bias: Optional[dict[str, int]] = None
    logprobs: bool = False
    max_completion_tokens: Optional[int] = None
    metadata: Optional[dict[str, str]] = None
    modalities: Optional[list[str]] = None
    n: int = 1
    parallel_tool_calls: bool = True
    prediction: Optional[object] = None
    presence_penalty: float = 0.0  # range: (-2.0, 2.0)
    reasoning_effort: str = "medium"  # low, medium or high
    response_format: Optional[object] = None
    seed: Optional[int] = None  # see system_fingerprint to monitor backend changes
    # service_tier: str = "auto"
    stop: Optional[str | list[str]] = None  # max length: 4
    # store: bool = False
    stream: bool = False
    stream_options: Optional[object] = None
    temperature: float = 1.0  # range: [0.0, 2.0]
    tool_choice: Optional[str | object] = None
    tools: Optional[list[dict[str, str]]] = None
    top_logprobs: Optional[int] = None
    top_p: float = 1.0  # range: [0.0, 1.0]
    # user: Optional[str] = None
    # web_search_options: Optional[object] = None

    # Sampling Parameters
    best_of: Optional[int] = None
    use_beam_search: bool = False
    top_k: Optional[int] = None
    min_p: Optional[float] = None
    repetition_penalty: Optional[float] = None
    length_penalty: float = 1.0
    stop_token_ids: Optional[list[int]] = None
    include_stop_str_in_output: bool = False
    ignore_eos: bool = False
    min_tokens: int = 0
    skip_special_tokens: bool = True
    spaces_between_special_tokens: bool = True
    truncate_prompt_tokens: Optional[Annotated[int, Field(ge=1)]] = None
    prompt_logprobs: Optional[int] = None

    # vLLM Extras
    echo: bool = Field(
        default=False,
        description=(
            "If true, the new message will be prepended with the last message "
            "if they belong to the same role."
        ),
    )
    add_generation_prompt: bool = Field(
        default=True,
        description=(
            "If true, the generation prompt will be added to the chat template. "
            "This is a parameter used by chat template in tokenizer config of the "
            "model."
        ),
    )
    continue_final_message: bool = Field(
        default=False,
        description=(
            "If this is set, the chat will be formatted so that the final "
            "message in the chat is open-ended, without any EOS tokens. The "
            "model will continue this message rather than starting a new one. "
            'This allows you to "prefill" part of the model\'s response for it. '
            "Cannot be used at the same time as `add_generation_prompt`."
        ),
    )
    add_special_tokens: bool = Field(
        default=False,
        description=(
            "If true, special tokens (e.g. BOS) will be added to the prompt "
            "on top of what is added by the chat template. "
            "For most models, the chat template takes care of adding the "
            "special tokens so this should be set to false (as is the "
            "default)."
        ),
    )
    documents: Optional[list[dict[str, str]]] = Field(
        default=None,
        description=(
            "A list of dicts representing documents that will be accessible to "
            "the model if it is performing RAG (retrieval-augmented generation)."
            " If the template does not support RAG, this argument will have no "
            "effect. We recommend that each document should be a dict containing "
            '"title" and "text" keys.'
        ),
    )
    chat_template: Optional[str] = Field(
        default=None,
        description=(
            "A Jinja template to use for this conversion. "
            "As of transformers v4.44, default chat template is no longer "
            "allowed, so you must provide a chat template if the tokenizer "
            "does not define one."
        ),
    )
    chat_template_kwargs: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Additional kwargs to pass to the template renderer. "
            "Will be accessible by the chat template."
        ),
    )
    mm_processor_kwargs: Optional[dict[str, Any]] = Field(
        default=None,
        description=("Additional kwargs to pass to the HF processor."),
    )
    guided_json: Optional[Union[str, dict[str, str], BaseModel]] = Field(
        default=None,
        description=("If specified, the output will follow the JSON schema."),
    )
    guided_regex: Optional[str] = Field(
        default=None,
        description=("If specified, the output will follow the regex pattern."),
    )
    guided_choice: Optional[list[str]] = Field(
        default=None,
        description=("If specified, the output will be exactly one of the choices."),
    )
    guided_grammar: Optional[str] = Field(
        default=None,
        description=("If specified, the output will follow the context free grammar."),
    )
    guided_decoding_backend: Optional[str] = Field(
        default=None,
        description=(
            "If specified, will override the default guided decoding backend "
            "of the server for this specific request. If set, must be either "
            "'outlines' / 'lm-format-enforcer'"
        ),
    )
    guided_whitespace_pattern: Optional[str] = Field(
        default=None,
        description=(
            "If specified, will override the default whitespace pattern "
            "for guided json decoding."
        ),
    )
    priority: int = Field(
        default=0,
        description=(
            "The priority of the request (lower means earlier handling; "
            "default: 0). Any priority other than 0 will raise an error "
            "if the served model does not use priority scheduling."
        ),
    )
    # request_id: str = Field(
    #     default_factory=lambda: f"{random_uuid()}",
    #     description=(
    #         "The request_id related to this request. If the caller does "
    #         "not set it, a random_uuid will be generated. This id is used "
    #         "through out the inference process and return in response."),
    # )
    # logits_processors: Optional[LogitsProcessors] = Field(
    #     default=None,
    #     description=(
    #         "A list of either qualified names of logits processors, or "
    #         "constructor objects, to apply when sampling. A constructor is "
    #         "a JSON object with a required 'qualname' field specifying the "
    #         "qualified name of the processor class/factory, and optional "
    #         "'args' and 'kwargs' fields containing positional and keyword "
    #         "arguments. For example: {'qualname': "
    #         "'my_module.MyLogitsProcessor', 'args': [1, 2], 'kwargs': "
    #         "{'param': 'value'}}."))
    return_tokens_as_token_ids: Optional[bool] = Field(
        default=None,
        description=(
            "If specified with 'logprobs', tokens are represented "
            " as strings of the form 'token_id:{token_id}' so that tokens "
            "that are not JSON-encodable can be identified."
        ),
    )


class TextGeneration(Service):
    """A containerized service running a text-generation API."""

    __mapper_args__ = {
        "polymorphic_identity": "text_generation",
    }

    async def __call__(
        self, inputs: str, params: TextGenerationParameters
    ) -> requests.Response:
        logger.info(f"calling service {self.id}")
        try:
            headers = {
                "Content-Type": "application/json",
            }
            body = {
                "inputs": inputs,
                "parameters": asdict(params),
            }
            res = requests.post(
                f"http://localhost:{self.port}/generate", json=body, headers=headers
            )
        except Exception as e:
            raise e

        return res
