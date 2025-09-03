"""
Chat Interface - Manages user interface and conversation loop
"""


# SRP: This class has a single responsibility - managing user interaction.
# It handles the conversation loop, user input, command processing, and response display
# without mixing concerns with model configuration, tools, or storage management.
class ChatInterface:
    """Manages user interface and conversation loop"""

    def __init__(self, agent, config):
        self.agent = agent
        self.config = config

    def start_chat(self):
        """Start the main conversation loop"""
        self._show_welcome()

        while True:
            try:
                user_input = input("\n👤 You: ").strip()

                if self._handle_special_commands(user_input):
                    break

                if not user_input:
                    print("Please type something...")
                    continue

                self._get_agent_response(user_input)

            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 Conversation interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                break

    def _show_welcome(self):
        """Show welcome message"""
        print("🤖 QA Intelligence Chat Agent")
        print("=" * 50)

        model_config = self.config.get_model_config()
        print(f"Model: {model_config['provider']} / {model_config['id']}")
        print(f"Temperature: {model_config['temperature']}")
        print("=" * 50)
        print("Commands: 'exit', 'config', 'help'")
        print("=" * 50)

    def _handle_special_commands(self, user_input):
        """Handle special commands"""
        command = user_input.lower()

        if command in ["exit", "quit", "bye", "salir"]:
            print("\n👋 Goodbye!")
            return True

        elif command == "config":
            print("\n📋 Current configuration:")
            self.config.print_summary()
            return False

        elif command == "help":
            self._show_help()
            return False

        return False

    def _show_help(self):
        """Show help commands"""
        print("\n📖 Available commands:")
        print("  config - Show current configuration")
        print("  help - Show this help")
        print("  exit/quit - End conversation")

    def _get_agent_response(self, user_input):
        """Get and display agent response"""
        print("\n🤖 Agent:", end=" ")
        try:
            response = self.agent.run(user_input)
            print(response.content)
        except Exception as e:
            print(f"Error getting response: {e}")
