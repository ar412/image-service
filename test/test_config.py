import pytest
import os
import importlib
from src import config


@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """Ensure APP_ENV is clean before and after each test."""
    original_app_env = os.environ.get("APP_ENV")
    original_localstack_hostname = os.environ.get("LOCALSTACK_HOSTNAME")
    if "APP_ENV" in os.environ:
        del os.environ["APP_ENV"]
    if "LOCALSTACK_HOSTNAME" in os.environ:
        del os.environ["LOCALSTACK_HOSTNAME"]
    yield
    if original_app_env is not None:
        os.environ["APP_ENV"] = original_app_env
    elif "APP_ENV" in os.environ:
        del os.environ["APP_ENV"]
    if original_localstack_hostname is not None:
        os.environ["LOCALSTACK_HOSTNAME"] = original_localstack_hostname
    elif "LOCALSTACK_HOSTNAME" in os.environ:
        del os.environ["LOCALSTACK_HOSTNAME"]


def test_get_config_local():
    os.environ["APP_ENV"] = "local"
    os.environ["LOCALSTACK_HOSTNAME"] = "my-localstack"
    # Reload the config module to re-evaluate the config object with the new env vars.
    reloaded_config = importlib.reload(config)
    assert isinstance(reloaded_config.config, config.LocalConfig)
    assert reloaded_config.config.S3_ENDPOINT_URL == "http://my-localstack:4566"
    assert reloaded_config.config.BOTO3_CREDENTIALS["aws_access_key_id"] == "test"


def test_get_config_stage_and_prod():
    reloaded_config = importlib.reload(config) # Reload to get default (prod)
    assert isinstance(reloaded_config.config, config.ProductionConfig)
    os.environ["APP_ENV"] = "stage"
    reloaded_config = importlib.reload(config) # Reload again to get stage config
    assert isinstance(reloaded_config.config, config.StagingConfig)
    assert reloaded_config.config.S3_ENDPOINT_URL is None  # Should be None for non-local