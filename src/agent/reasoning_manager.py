"""
Reasoning Manager - Handles different reasoning approaches for QA Agent
"""


# SRP: This class has a single responsibility - managing reasoning capabilities.
# It encapsulates different reasoning approaches (models, tools, agents) without
# mixing concerns with model configuration, storage, or user interface.
class ReasoningManager:
    """Manages reasoning capabilities for enhanced QA intelligence"""

    def __init__(self, config):
        """
        Initialize reasoning manager with configuration

        Args:
            config: System configuration object
        """
        self.config = config
        self.reasoning_type = None
        self.reasoning_model = None
        self.reasoning_tools = []

    def setup_reasoning(self):
        """
        Setup reasoning based on configuration

        Returns:
            dict: Reasoning configuration for agent
        """
        reasoning_config = self.config.get_reasoning_config()

        if not reasoning_config.get("enabled", False):
            print("⚠️  Reasoning disabled")
            return {"reasoning": False}

        reasoning_type = reasoning_config.get("type", "tools")

        if reasoning_type == "model":
            return self._setup_reasoning_model(reasoning_config)
        elif reasoning_type == "tools":
            return self._setup_reasoning_tools(reasoning_config)
        elif reasoning_type == "agent":
            return self._setup_reasoning_agent(reasoning_config)
        else:
            print(f"⚠️  Unknown reasoning type: {reasoning_type}")
            return {"reasoning": False}

    def _setup_reasoning_model(self, config):
        """Setup reasoning model approach"""
        try:
            model_id = config.get("model_id", "o3-mini")

            if "o3" in model_id or "o1" in model_id:
                from agno.models.openai import OpenAIChat

                self.reasoning_model = OpenAIChat(id=model_id)
                print(f"✅ Reasoning model enabled: {model_id}")
                return {"reasoning_model": self.reasoning_model}

            elif "deepseek" in model_id.lower():
                from agno.models.groq import Groq

                self.reasoning_model = Groq(
                    id=model_id, temperature=0.6, max_tokens=1024, top_p=0.95
                )
                print(f"✅ Reasoning model enabled: {model_id}")
                return {"reasoning_model": self.reasoning_model}

            else:
                print(f"⚠️  Unsupported reasoning model: {model_id}")
                return {"reasoning": False}

        except ImportError as e:
            print(f"⚠️  Reasoning model not available: {e}")
            return {"reasoning": False}

    def _setup_reasoning_tools(self, config):
        """Setup reasoning tools approach"""
        try:
            from agno.tools.thinking import ThinkingTools

            thinking_tool = ThinkingTools(
                add_instructions=config.get("add_instructions", True)
            )
            self.reasoning_tools.append(thinking_tool)

            print("✅ Reasoning tools enabled (ThinkingTools)")
            return {
                "tools": self.reasoning_tools,
                "reasoning_params": {
                    "show_full_reasoning": True,
                    "stream_intermediate_steps": True,
                },
            }

        except ImportError as e:
            print(f"⚠️  Reasoning tools not available: {e}")
            return {"reasoning": False}

    def _setup_reasoning_agent(self, config):
        """Setup reasoning agent approach"""
        try:
            print("✅ Reasoning agent enabled")
            return {
                "reasoning": True,
                "reasoning_params": {
                    "show_full_reasoning": True,
                    "stream_intermediate_steps": True,
                },
            }

        except Exception as e:
            print(f"⚠️  Reasoning agent setup failed: {e}")
            return {"reasoning": False}

    def get_reasoning_info(self):
        """
        Get reasoning configuration information

        Returns:
            dict: Reasoning information
        """
        reasoning_config = self.config.get_reasoning_config()

        return {
            "enabled": reasoning_config.get("enabled", False),
            "type": reasoning_config.get("type", "disabled"),
            "model": getattr(self.reasoning_model, "id", None),
            "tools_count": len(self.reasoning_tools),
        }
