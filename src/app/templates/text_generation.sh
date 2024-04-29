{% extends "base-local.sh" %}
{% block command %}
docker {{ '--nv' if job_config.gres > 0 else '' }} run \
--bind {{ job_config.cache_dir }}/huggingface/data:/data \
{{ job_config.cache_dir }}/huggingface/images/text-generation-inference_latest.sif \
--model-id /data/{{ model }} \
--port $port{% for key,value in options.items() %} --{{ key }} {{ value }}{% endfor %}
{% endblock %}