"""
Integration test for run_qa_agent entrypoint.

Runs the main() function with a stub ChatInterface to avoid
interactive input and external API calls. Ensures exit code is 0.
"""

import os
import sys
import types


def test_run_qa_agent_entrypoint(monkeypatch, capsys):
    """Run run_qa_agent.main() with patched ChatInterface and env."""
    # Ensure an API key exists for config validation
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Prepare a stub ChatInterface module to avoid interactive loop
    stub_module = types.ModuleType("chat_interface")

    class StubChatInterface:
        def __init__(self, agent, config):
            self.agent = agent
            self.config = config

        def start_chat(self):
            # Print a sentinel to assert the interface was invoked
            print("[StubChatInterface] start_chat called")

    setattr(stub_module, "ChatInterface", StubChatInterface)
    sys.modules["chat_interface"] = stub_module

    # Inject minimal agno stubs to avoid external dependencies
    agno_pkg = types.ModuleType("agno")
    agno_agent_mod = types.ModuleType("agno.agent")

    class StubAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run(self, text):
            class R:
                content = "stub"

            return R()

    agno_agent_mod.Agent = StubAgent
    sys.modules["agno"] = agno_pkg
    sys.modules["agno.agent"] = agno_agent_mod

    agno_models_openai = types.ModuleType("agno.models.openai")

    class StubOpenAIChat:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    agno_models_openai.OpenAIChat = StubOpenAIChat
    sys.modules["agno.models.openai"] = agno_models_openai

    # Stub minimal tool modules used by ToolsManager
    def _mk_tool_mod(cls_name):
        m = types.ModuleType(f"tool.{cls_name}")

        class _T:
            __name__ = cls_name

        _T.__name__ = cls_name
        setattr(m, cls_name, type(cls_name, (), {}) )
        return m

    duckduckgo_mod = types.ModuleType("agno.tools.duckduckgo")
    setattr(duckduckgo_mod, "DuckDuckGo", type("DuckDuckGo", (), {}))
    python_mod = types.ModuleType("agno.tools.python")
    setattr(python_mod, "PythonTools", type("PythonTools", (), {}))
    calc_mod = types.ModuleType("agno.tools.calculator")
    setattr(calc_mod, "CalculatorTools", type("CalculatorTools", (), {}))
    file_mod = types.ModuleType("agno.tools.file")
    setattr(file_mod, "FileTools", type("FileTools", (), {}))
    thinking_mod = types.ModuleType("agno.tools.thinking")
    setattr(thinking_mod, "ThinkingTools", type("ThinkingTools", (), {}))

    sys.modules["agno.tools.duckduckgo"] = duckduckgo_mod
    sys.modules["agno.tools.python"] = python_mod
    sys.modules["agno.tools.calculator"] = calc_mod
    sys.modules["agno.tools.file"] = file_mod
    sys.modules["agno.tools.thinking"] = thinking_mod

    # Stub the model_manager to avoid pydantic/config dependencies
    model_manager_mod = types.ModuleType("model_manager")

    class StubModelManager:
        def __init__(self, config):
            self.config = config

        def create_model(self):
            return object()

        def get_model_info(self):
            return {"provider": "stub", "id": "stub-model"}

    setattr(model_manager_mod, "ModelManager", StubModelManager)
    sys.modules["model_manager"] = model_manager_mod

    # Provide a minimal config module to avoid reading YAML/env deps
    cfg_mod = types.ModuleType("config")

    class _Cfg:
        def validate_config(self):
            return True

        def get_model_config(self):
            return {
                "provider": "openai",
                "id": "gpt-3.5-turbo",
                "temperature": 0.1,
                "api_key": os.getenv("OPENAI_API_KEY", "test-key"),
            }

        def get_enabled_tools(self):
            return {
                "web_search": True,
                "python_execution": True,
                "file_operations": False,
                "calculator": True,
            }

        def get_interface_config(self):
            return {"show_tool_calls": False, "enable_markdown": False}

        def get_agent_instructions(self):
            return ["You are a test agent."]

        def get_reasoning_config(self):
            return {"enabled": False, "type": "agent", "model_id": "o3-mini"}

        def get_database_config(self):
            return {"conversations_path": "data/qa_conversations.db"}

    def get_config():
        return _Cfg()

    cfg_mod.get_config = get_config
    sys.modules["config"] = cfg_mod

    # Import the entrypoint after injecting stubs
    import run_qa_agent

    # Run with flags that minimize side effects
    exit_code = run_qa_agent.main([
        "--user-id", "test@qai.com",
        "--reasoning", "off",
        "--no-memory",
    ])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "StubChatInterface" in out
