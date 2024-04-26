{% extends "base-local.sh" %}
{% block command %}
docker {{ '--nv' if job_config.gres > 0 else '' }} run \
--bind {{ app_config.model_cache }}/huggingface/data:/data \
{{ app_config.image_cache }}/huggingface/images/text-generation-inference_latest.sif \
--model-id /data/{{ model }} \
--port $port{% for key,value in options.items() %} --{{ key }} {{ value }}{% endfor %}
{% endblock %}