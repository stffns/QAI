"""
Response Manager - Controls response length and reasoning activation
Optimizes model responses for conciseness vs detail based on context
"""

import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

# Configure logging
try:
    from ..logging_config import get_logger, LogStep
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from logging_config import get_logger, LogStep

logger = get_logger("ResponseManager")


@dataclass
class ResponseContext:
    """Context for determining response strategy"""
    user_message: str
    session_history: Optional[List[str]] = None
    requires_reasoning: bool = False
    concise_mode: bool = True
    max_tokens: int = 300
    # Cost optimization fields
    strategy_name: str = "concise"
    is_simple: bool = False
    recommended_model: str = "gpt-5-mini"


class ResponseStrategy:
    """Response strategy configuration"""
    
    def __init__(self, 
                 name: str,
                 max_tokens: int,
                 temperature: float,
                 system_prompt: str):
        self.name = name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt


class ResponseManager:
    """
    Manages response optimization for QA Intelligence
    
    Features:
    - Automatic reasoning detection
    - Concise vs detailed response selection
    - Token limit optimization
    - Context-aware response strategies
    """
    
    def __init__(self, config):
        """
        Initialize response manager with configuration
        
        Args:
            config: System configuration object
        """
        self.config = config
        self._load_strategies()
        self._load_reasoning_config()
    
    def _load_reasoning_config(self):
        """Load reasoning configuration"""
        try:
            # Try to get reasoning config from the system
            if hasattr(self.config, 'get_reasoning_config'):
                self.reasoning_config = self.config.get_reasoning_config()
            else:
                # Fallback configuration
                self.reasoning_config = {
                    "enabled": True,
                    "auto_reasoning": False,
                    "triggers": [
                        "explain in detail", "analyze", "complex reasoning",
                        "step by step", "comprehensive", "elaborate",
                        "how does", "why does", "what are the implications",
                        "compare", "contrast", "pros and cons"
                    ],
                    "concise_mode": True,
                    "max_concise_tokens": 300
                }
            
            logger.debug(f"Reasoning config loaded: {self.reasoning_config}")
            
        except Exception as e:
            logger.warning(f"Failed to load reasoning config, using defaults: {e}")
            self.reasoning_config = {
                "enabled": True,
                "auto_reasoning": False,
                "triggers": ["explain in detail", "analyze", "step by step"],
                "concise_mode": True,
                "max_concise_tokens": 300
            }
    
    def _load_strategies(self):
        """Load response strategies with cost-optimized GPT-5 model selection"""
        self.strategies = {
            "nano": ResponseStrategy(
                name="nano",
                max_tokens=100,
                temperature=1.0,  # Required for gpt-5-nano
                system_prompt="""You are an ultra-concise assistant. Provide the shortest possible answer:
- One sentence maximum
- Direct answers only
- No explanations unless critical
- Perfect for yes/no, greetings, confirmations"""
            ),
            
            "concise": ResponseStrategy(
                name="concise",
                max_tokens=300,
                temperature=1.0,  # Required for gpt-5-mini
                system_prompt="""You are a concise QA assistant. Provide direct, focused answers:
- Keep responses under 3 sentences when possible
- Use bullet points for lists  
- Avoid unnecessary explanations unless explicitly asked
- For complex topics, ask if the user wants more detail
- Be helpful but brief"""
            ),
            
            "detailed": ResponseStrategy(
                name="detailed", 
                max_tokens=1500,
                temperature=0.3,  # Adjustable for gpt-5 (focused reasoning)
                system_prompt="""You are a comprehensive QA assistant. Provide thorough, detailed answers:
- Explain concepts fully with context
- Include relevant examples and background
- Break down complex topics step by step
- Provide comprehensive analysis when requested
- Use structured formatting for clarity"""
            ),
            
            "balanced": ResponseStrategy(
                name="balanced",
                max_tokens=600,
                temperature=0.5,
                system_prompt="""You are a balanced QA assistant. Provide clear, informative answers:
- Give enough detail to be helpful without being verbose
- Include key points and essential context
- Use examples when they clarify the explanation
- Structure responses for easy reading
- Balance brevity with completeness"""
            )
        }
        
        logger.debug(f"Loaded {len(self.strategies)} response strategies with cost optimization")
    
    def analyze_message(self, user_message: str, session_history: Optional[List[str]] = None) -> ResponseContext:
        """
        Analyze user message to determine optimal response strategy with cost optimization
        
        Args:
            user_message: User's input message
            session_history: Previous messages in the session
            
        Returns:
            ResponseContext with strategy recommendations including model selection
        """
        with LogStep("Analyzing message for response strategy", "ResponseManager"):
            
            # Check for ultra-simple interactions (nano model)
            is_simple = self._check_simple_interaction(user_message)
            
            # Check for reasoning triggers (full model)
            requires_reasoning = self._check_reasoning_triggers(user_message)
            
            # Determine response strategy
            if is_simple and self.reasoning_config.get("cost_optimization", True):
                strategy_name = "nano"
                concise_mode = True
                max_tokens = 100
            elif requires_reasoning:
                strategy_name = "detailed"
                concise_mode = False
                max_tokens = 1500
            else:
                # Default to concise with mini model
                concise_mode = self._should_use_concise_mode(user_message, requires_reasoning)
                strategy_name = "concise" if concise_mode else "balanced"
                max_tokens = self._get_token_limit(concise_mode, requires_reasoning)
            
            context = ResponseContext(
                user_message=user_message,
                session_history=session_history,
                requires_reasoning=requires_reasoning,
                concise_mode=concise_mode,
                max_tokens=max_tokens
            )
            
            # Add model selection info
            context.strategy_name = strategy_name
            context.is_simple = is_simple
            context.recommended_model = self._get_recommended_model(strategy_name, is_simple, requires_reasoning)
            
            logger.info(f"Response strategy: {strategy_name}, "
                       f"reasoning: {requires_reasoning}, "
                       f"simple: {is_simple}, "
                       f"model: {context.recommended_model}, "
                       f"tokens: {max_tokens}")
            
            return context
    
    def _get_recommended_model(self, strategy_name: str, is_simple: bool, requires_reasoning: bool) -> str:
        """Get recommended model based on interaction complexity"""
        if is_simple and self.reasoning_config.get("cost_optimization", True):
            simple_model = self.reasoning_config.get("simple_model", {})
            return simple_model.get("id", "gpt-5-nano")
        elif requires_reasoning:
            reasoning_model = self.reasoning_config.get("reasoning_model", {})
            return reasoning_model.get("id", "gpt-5")
        else:
            # Default to mini model for regular interactions
            return "gpt-5-mini"
    
    def _check_simple_interaction(self, message: str) -> bool:
        """Check if message is a simple interaction suitable for nano model"""
        if not self.reasoning_config.get("cost_optimization", True):
            return False
        
        simple_config = self.reasoning_config.get("simple_model", {})
        simple_triggers = simple_config.get("triggers", [])
        
        message_lower = message.lower().strip()
        
        # Check for simple triggers
        for trigger in simple_triggers:
            if trigger.lower() in message_lower:
                logger.debug(f"Simple interaction trigger found: '{trigger}'")
                return True
        
        # Check for very short messages (likely simple)
        if len(message.split()) <= 3:
            # Common simple patterns
            simple_patterns = [
                r'^(hi|hello|hey|hola)$',
                r'^(yes|no|si|no)$', 
                r'^(thanks?|thank you|gracias)$',
                r'^(ok|okay|bien)$',
                r'^(bye|goodbye|adios)$'
            ]
            
            for pattern in simple_patterns:
                if re.search(pattern, message_lower):
                    logger.debug(f"Simple pattern matched: {pattern}")
                    return True
        
        return False
    
    def _check_reasoning_triggers(self, message: str) -> bool:
        """Check if message contains reasoning triggers"""
        if not self.reasoning_config.get("enabled", True):
            return False
        
        if self.reasoning_config.get("auto_reasoning", False):
            return True
        
        triggers = self.reasoning_config.get("triggers", [])
        message_lower = message.lower()
        
        for trigger in triggers:
            if trigger.lower() in message_lower:
                logger.debug(f"Reasoning trigger found: '{trigger}'")
                return True
        
        # Check for question complexity indicators
        complexity_indicators = [
            r"\bwhy\b.*\bhow\b",  # Questions asking both why and how
            r"\bcomplex\b",       # Explicit complexity mentions
            r"\bdetailed?\s+(explanation|analysis|breakdown)\b",
            r"\bstep\s+by\s+step\b",
            r"\bpros\s+and\s+cons\b",
            r"\bcompare\s+(and\s+contrast|with)\b"
        ]
        
        for pattern in complexity_indicators:
            if re.search(pattern, message_lower):
                logger.debug(f"Complexity indicator found: {pattern}")
                return True
        
        return False
    
    def _should_use_concise_mode(self, message: str, requires_reasoning: bool) -> bool:
        """Determine if concise mode should be used"""
        # Override concise mode if reasoning is required
        if requires_reasoning:
            return False
        
        # Check for explicit conciseness requests
        concise_requests = [
            "brief", "short", "quick", "summary", "in short",
            "tldr", "concise", "briefly", "simple answer"
        ]
        
        message_lower = message.lower()
        for request in concise_requests:
            if request in message_lower:
                logger.debug(f"Concise request found: '{request}'")
                return True
        
        # Default to concise mode if configured
        return self.reasoning_config.get("concise_mode", True)
    
    def _get_token_limit(self, concise_mode: bool, requires_reasoning: bool) -> int:
        """Get appropriate token limit based on strategy"""
        if requires_reasoning:
            return self.strategies["detailed"].max_tokens
        elif concise_mode:
            return self.reasoning_config.get("max_concise_tokens", 300)
        else:
            return self.strategies["balanced"].max_tokens
    
    def get_strategy(self, context: ResponseContext) -> ResponseStrategy:
        """
        Get response strategy based on context
        
        Args:
            context: Response context from analyze_message
            
        Returns:
            ResponseStrategy configuration
        """
        strategy_name = getattr(context, 'strategy_name', 'concise')
        return self.strategies.get(strategy_name, self.strategies['concise'])
    
    def get_model_config_override(self, context: ResponseContext) -> Dict[str, Any]:
        """
        Get model configuration override based on response context
        
        Args:
            context: Response context
            
        Returns:
            Dictionary with model configuration overrides
        """
        strategy = self.get_strategy(context)
        
        config_override = {
            "max_tokens": context.max_tokens,
            "temperature": strategy.temperature,
        }
        
        # Add system instructions if model supports it
        if hasattr(self.config, 'get_model_config'):
            model_config = self.config.get_model_config()
            if "system_instructions" in model_config or True:  # Always add for now
                config_override["system_instructions"] = strategy.system_prompt
        
        logger.debug(f"Model config override: {config_override}")
        return config_override
    
    def should_enable_streaming(self, context: ResponseContext) -> bool:
        """
        Determine if streaming should be enabled based on context
        
        Args:
            context: Response context
            
        Returns:
            Boolean indicating if streaming should be enabled
        """
        # Enable streaming for longer responses
        return context.max_tokens > 200 or context.requires_reasoning
    
    def get_stats(self) -> Dict[str, Any]:
        """Get response manager statistics with cost optimization info"""
        return {
            "strategies_available": list(self.strategies.keys()),
            "reasoning_enabled": self.reasoning_config.get("enabled", False),
            "concise_mode_default": self.reasoning_config.get("concise_mode", True),
            "reasoning_triggers": len(self.reasoning_config.get("triggers", [])),
            "max_concise_tokens": self.reasoning_config.get("max_concise_tokens", 300),
            "cost_optimization": self.reasoning_config.get("cost_optimization", True),
            "models_configured": {
                "default": "gpt-5-mini",
                "reasoning": self.reasoning_config.get("reasoning_model", {}).get("id", "gpt-5"),
                "simple": self.reasoning_config.get("simple_model", {}).get("id", "gpt-5-nano")
            }
        }
