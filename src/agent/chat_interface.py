"""
Chat Interface - Manages user interface and conversation loop with streaming support
"""

import sys
import time
from typing import Iterator, Any


# SRP: This class has a single responsibility - managing user interaction.
# It handles the conversation loop, user input, command processing, streaming responses,
# and response display without mixing concerns with model configuration, tools, or storage management.
class ChatInterface:
    """Manages user interface and conversation loop with streaming support"""

    def __init__(self, agent, config):
        self.agent = agent
        self.config = config
        self._streaming_enabled = self._get_streaming_config()

    def _get_streaming_config(self) -> dict:
        """Get streaming configuration from config"""
        try:
            interface_config = self.config.get_interface_config()
            return interface_config.get("terminal", {}).get("streaming", {
                "enabled": True,
                "show_cursor": True,
                "cursor_style": "⚡",
                "typing_delay": 0.02
            })
        except:
            return {
                "enabled": True,
                "show_cursor": True, 
                "cursor_style": "⚡",
                "typing_delay": 0.02
            }

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
        """Get and display agent response with streaming support"""
        print("\n🤖 Agent:", end=" ")
        
        # Check if streaming is enabled in configuration
        model_config = self.config.get_model_config()
        stream_enabled = model_config.get("stream", False)
        
        try:
            response = self.agent.run(user_input)
            
            # Handle streaming response
            if stream_enabled and hasattr(response, '__iter__') and not hasattr(response, 'content'):
                # Response is a generator (streaming mode)
                for chunk in response:
                    if hasattr(chunk, 'content') and chunk.content:
                        self._print_chunk(chunk.content)
                    elif isinstance(chunk, str):
                        self._print_chunk(chunk)
                    elif hasattr(chunk, 'delta') and hasattr(chunk.delta, 'content') and chunk.delta.content:
                        self._print_chunk(chunk.delta.content)
                print()  # Final newline
            else:
                # Regular response object or non-streaming
                if hasattr(response, 'content'):
                    if self._streaming_enabled.get("enabled", False):
                        self._simulate_typing(response.content)
                    else:
                        print(response.content)
                else:
                    print(str(response))
                    
        except Exception as e:
            print(f"Error getting response: {e}")
            import traceback
            traceback.print_exc()

    def _display_streaming_response(self, user_input):
        """Display real streaming response from agent"""
        try:
            for chunk in self.agent.stream(user_input):
                if hasattr(chunk, 'content') and chunk.content:
                    self._print_chunk(chunk.content)
                elif isinstance(chunk, str):
                    self._print_chunk(chunk)
            print()  # Final newline
        except Exception as e:
            print(f"\nStreaming error: {e}")
            
    def _display_streaming_response_fallback(self, user_input):
        """Fallback streaming using model directly"""
        try:
            # This would need to be implemented based on Agno's streaming API
            response = self.agent.run(user_input)
            self._simulate_typing(response.content)
        except Exception as e:
            print(f"Fallback streaming error: {e}")

    def _simulate_streaming_response(self, user_input):
        """Simulate streaming by typing out the response"""
        try:
            response = self.agent.run(user_input)
            self._simulate_typing(response.content)
        except Exception as e:
            print(f"Error getting response: {e}")

    def _print_chunk(self, chunk: str):
        """Print a chunk with optional delay"""
        print(chunk, end="", flush=True)
        if self._streaming_enabled.get("typing_delay", 0) > 0:
            time.sleep(self._streaming_enabled["typing_delay"])

    def _simulate_typing(self, text: str):
        """Simulate typing effect for non-streaming responses"""
        typing_delay = self._streaming_enabled.get("typing_delay", 0.02)
        
        for char in text:
            print(char, end="", flush=True)
            if typing_delay > 0:
                time.sleep(typing_delay)
        print()  # Final newline

    def _show_streaming_cursor(self):
        """Show animated cursor during thinking"""
        cursor = self._streaming_enabled.get("cursor_style", "⚡")
        print(f"{cursor} Thinking...", end="", flush=True)
        time.sleep(0.5)
        print("\r" + " " * 20 + "\r", end="", flush=True)  # Clear cursor
