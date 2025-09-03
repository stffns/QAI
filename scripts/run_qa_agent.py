#!/usr/bin/env python3
"""
Executable script for the QA Agent with Reasoning capabilities
"""

import os
import sys


def main():
    """Execute the QA Agent with reasoning support"""
    try:
        # Change working directory to project root
        project_root = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_root)

        # Add project root to Python path
        sys.path.insert(0, project_root)

        # Import core dependencies
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat

        from config import get_config

        # Add agent directory to path and import modular components
        agent_dir = os.path.join(project_root, "src", "agent")
        sys.path.insert(0, agent_dir)

        from chat_interface import ChatInterface
        from model_manager import ModelManager
        from storage_manager import StorageManager
        from tools_manager import ToolsManager

        # Initialize configuration
        config = get_config()

        if not config.validate_config():
            raise ValueError("Invalid configuration")

        # Create component managers
        model_manager = ModelManager(config)
        tools_manager = ToolsManager(config)
        storage_manager = StorageManager(config)

        # Create components
        model = model_manager.create_model()
        tools = tools_manager.load_tools()
        storage = storage_manager.setup_storage()

        # Get configuration
        interface_config = config.get_interface_config()
        instructions = config.get_agent_instructions()
        reasoning_config = config.get_reasoning_config()

        # Get QA context user_id - default para QA Intelligence
        user_id = "qa_analyst@qai.com"  # Contexto por defecto para QA

        # Prepare agent arguments
        agent_args = {
            "model": model,
            "instructions": instructions,
            "tools": tools,
            "memory": storage,
            "show_tool_calls": interface_config.get("show_tool_calls", True),
            "markdown": interface_config.get("enable_markdown", True),
            "add_history_to_messages": storage is not None,
            "user_id": user_id,  # ⭐ Contexto de usuario QA
        }

        # Add advanced memory capabilities if storage is available
        if storage is not None:
            agent_args.update(
                {
                    "enable_user_memories": True,  # ⭐ Memoria automática de usuario
                    "enable_agentic_memory": True,  # ⭐ Gestión inteligente de memoria
                    "num_history_runs": 5,  # Más contexto histórico
                }
            )
            print("✅ Advanced Memory: User memories and agentic management enabled")

        # Add reasoning if enabled
        if reasoning_config.get("enabled", False):
            reasoning_type = reasoning_config.get("type", "agent")

            if reasoning_type == "agent":
                # Simple reasoning agent - just set reasoning=True
                agent_args["reasoning"] = True
                print("✅ Reasoning Agent enabled (chain-of-thought)")

            elif reasoning_type == "model":
                # Reasoning model approach
                model_id = reasoning_config.get("model_id", "o3-mini")
                try:
                    if "o3" in model_id or "o1" in model_id:
                        reasoning_model = OpenAIChat(id=model_id)
                        agent_args["reasoning_model"] = reasoning_model
                        print(f"✅ Reasoning Model enabled: {model_id}")
                    else:
                        print(f"⚠️  Unsupported reasoning model: {model_id}")
                except Exception as e:
                    print(f"⚠️  Reasoning model setup failed: {e}")

            elif reasoning_type == "tools":
                # Reasoning tools approach
                try:
                    from agno.tools.thinking import ThinkingTools

                    thinking_tool = ThinkingTools(
                        add_instructions=reasoning_config.get("add_instructions", True)
                    )
                    agent_args["tools"].append(thinking_tool)
                    print("✅ Reasoning Tools enabled (ThinkingTools)")
                except ImportError as e:
                    print(f"⚠️  Reasoning tools not available: {e}")

        # Create agent
        agent = Agent(**agent_args)

        # Create and run chat interface
        chat_interface = ChatInterface(agent, config)
        chat_interface.start_chat()

    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        print("Please check your configuration by running: python config.py")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
