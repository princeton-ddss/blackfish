from typing import Any

import pytest

from app.services.base import Service
from app.services.speech_recognition import SpeechRecognition
from app.services.text_generation import TextGeneration
from app.jobs.base import BatchJob
from app.jobs.speech_recognition import SpeechRecognitionBatch
from app.models.model import Model

pytestmark = pytest.mark.anyio


@pytest.fixture(name="services")
def services_fixture() -> list[Service | dict[str, Any]]:
    return [
        {
            "class": SpeechRecognition,
            "data": {
                "id": "4c2216ea-df22-4bf6-bcea-56964df12af5",
                "name": "blackfish-1",
                "image": "speech_recognition",
                "model": "openai/whisper-large-v3",
                "profile": "test",
                "host": "localhost",
                "user": "test",
                "grace_period": 60,
            },
        },
        {
            "class": SpeechRecognition,
            "data": {
                "id": "7f92a3f7-418f-4957-9e9c-f2bbda39392a",
                "name": "blackfish-2",
                "image": "speech_recognition",
                "model": "openai/whisper-large-v3",
                "profile": "test-slurm",
                "host": "test-server",
                "user": "test",
                "grace_period": 60,
            },
        },
        {
            "class": TextGeneration,
            "data": {
                "id": "8c7184b0-95f4-4ec1-92b9-ddfedee48395",
                "name": "blackfish-3",
                "image": "text_generation",
                "model": "tiny-llama/tiny-llama-1.1b-v1.0",
                "profile": "test",
                "host": "localhost",
                "user": "test",
                "grace_period": 60,
            },
        },
        {
            "class": TextGeneration,
            "data": {
                "id": "14fd672d-4387-4276-b466-9fdf1784e1cb",
                "name": "blackfish-4",
                "image": "text_generation",
                "model": "meta-llama/Llama-3.2-3B",
                "profile": "test",
                "host": "localhost",
                "user": "test",
                "grace_period": 60,
            },
        },
    ]


@pytest.fixture(name="jobs")
def batch_jobs_fixture() -> list[BatchJob | dict[str, Any]]:
    return [
        {
            "class": SpeechRecognitionBatch,
            "data": {
                "id": "2a7a8e62-40cc-4240-a825-463e5b11a81f",
                "name": "blackfish-1",
                "pipeline": "speech_recognition",
                "repo_id": "openai/whisper-large-v3",
                "profile": "test",
                "user": "test",
                "host": "localhost",
            },
        },
        {
            "class": SpeechRecognitionBatch,
            "data": {
                "id": "391769fc-5a40-43db-bbfa-cec80a8c3710",
                "name": "blackfish-2",
                "pipeline": "speech_recognition",
                "repo_id": "openai/whisper-tiny",
                "profile": "test",
                "user": "test",
                "host": "localhost",
            },
        },
        {
            "class": SpeechRecognitionBatch,
            "data": {
                "id": "25058c41-9779-4b16-af6e-3fe5c3902435",
                "name": "blackfish-3",
                "pipeline": "speech_recognition",
                "repo_id": "openai/whisper-large-v3",
                "profile": "test-slurm",
                "user": "test",
                "host": "test-server",
            },
        },
    ]


@pytest.fixture(name="models")
def models_fixture() -> list[Model | dict[str, Any]]:
    return [
        {
            "id": "cc64bbef-816c-4070-941d-3dabece7a3b9",
            "repo": "openai/whisper-large-v3",
            "profile": "default",
            "revision": "1",
            "image": "speech_recognition",
            "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
        },
        {
            "id": "0022468b-3182-4381-a76a-25d06248398f",
            "repo": "openai/whisper-tiny",
            "profile": "default",
            "revision": "2",
            "image": "speech_recognition",
            "model_dir": "/home/test/.blackfish/models/models--openai/whisper-tiny",
        },
        {
            "id": "6eaaf298-951d-4073-87b5-13fd0cb9b803",
            "repo": "meta-llama/Llama-3.2-3B",
            "profile": "default",
            "revision": "3",
            "image": "text_generation",
            "model_dir": "/home/test/.blackfish/models/models--meta-llama/Llama-3.2-3B",
        },
        {
            "id": "64ef94e4-689d-4479-8023-6f5823897ee8",
            "repo": "meta-llama/Llama-3.1-70B",
            "profile": "default",
            "revision": "4",
            "image": "text_generation",
            "model_dir": "/home/test/.blackfish/models/models--meta-llama/Llama-3.1-70B",
        },
    ]
