from bloggeragent.config import Settings


def test_defaults(clean_env):
    s = Settings.from_env()
    assert s.model == "gemini-flash-latest"
    assert s.auth_mode == "api_key"
    assert s.max_loop_iterations == 3
    assert s.enable_memory is True and s.redact_pii is True
    assert s.allowed_origins == ["*"]
    assert s.artifact_service_uri is None and s.database_url is None


def test_cloud_env(clean_env):
    env = {
        "MODEL": "gemini-3.5-flash", "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "GOOGLE_CLOUD_LOCATION": "global", "ARTIFACT_BUCKET": "my-bucket",
        "ALLOWED_ORIGINS": "https://a.app, https://b.app", "MAX_LOOP_ITERATIONS": "5",
        "BLOCKED_TOPICS": "crypto scam,gambling", "ENABLE_MEMORY": "false",
        "MEMORY_SERVICE_URI": "agentengine://123", "LOG_LEVEL": "debug",
    }
    for k, v in env.items():
        clean_env.setenv(k, v)
    s = Settings.from_env()
    assert s.model == "gemini-3.5-flash" and s.auth_mode == "vertex"
    assert s.artifact_service_uri == "gs://my-bucket"
    assert s.allowed_origins == ["https://a.app", "https://b.app"]
    assert s.max_loop_iterations == 5
    assert s.blocked_topics == ("crypto scam", "gambling")
    assert s.enable_memory is False and s.memory_service_uri == "agentengine://123"
    assert s.log_level == "DEBUG"


def test_invalid_numbers_fall_back(clean_env):
    clean_env.setenv("MAX_LOOP_ITERATIONS", "abc")
    clean_env.setenv("MAX_INPUT_CHARS", "5")
    s = Settings.from_env()
    assert s.max_loop_iterations == 3 and s.max_input_chars == 100
