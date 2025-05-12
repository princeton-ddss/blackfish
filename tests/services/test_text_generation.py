import requests


def test_remote_slurm():
    data = {
        "name": "test-123",
        "image": "text_generation",
        "model": "bigscience/bloom-560m",
        "profile": "della",
        "user": "cs7101",
        "host": "della.princeton.edu",
        "home_dir": "/home/cs7101/.blackfish",
        "cache_dir": "/scratch/gpfs/ddsscloud/.blackfish",
        "scheduler": "slurm",
        "grace_period": 180,
        "mount": "/home/cs7101",
        "container_options": {"disable_custom_kernels": True, "revision": "latest"},
        "job_options": {
            "ntasks_per_node": 8,
            "mem": "16",
            "gres": 1,
            "time": "00:05:00",
        },
    }
    requests.post(
        "http://localhost:8000/services",
        data=data,
    )


def test_local_slurm():
    data = {
        "name": "test-123",
        "image": "text_generation",
        "model": "bigscience/bloom-560m",
        "profile": "default",
        "user": "cs7101",
        "host": "localhost",
        "home_dir": "/home/cs7101/.blackfish",
        "cache_dir": "/scratch/gpfs/ddsscloud/.blackfish",
        "scheduler": "slurm",
        "provider": "apptainer",
        "grace_period": 180,
        "mount": "/home/cs7101",
        "container_options": {"disable_custom_kernels": True, "revision": "latest"},
        "job_options": {
            "ntasks_per_node": 8,
            "mem": "16",
            "gres": 1,
            "time": "00:05:00",
        },
    }
    requests.post(
        "http://localhost:8000/services",
        data=data,
    )


def test_local():
    data = {
        "name": "test-123",
        "image": "text_generation",
        "model": "bigscience/bloom-560m",
        "profile": "default",
        "home_dir": "/home/cs7101/.blackfish",
        "cache_dir": "/home/cs7101/.blackfish",
        "provider": "docker",
        "grace_period": 180,
        "container_options": {"disable_custom_kernels": True, "revision": "latest"},
        "job_options": {
            "ntasks_per_node": 8,
            "mem": "16",
            "gres": 1,
            "time": "00:05:00",
        },
    }
    requests.post(
        "http://localhost:8000/services",
        data=data,
    )
