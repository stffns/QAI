#!/usr/bin/env python3
"""
🤖 QA Intelligence Team Implementation
=====================================

Implementación práctica de agno.team.Team para QA Intelligence.
Crear equipos especializados de agentes QA colaborativos.

Author: QA Intelligence Team
Date: September 2025
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.team import Team

# Import project configuration
try:
    from config import Config
except ImportError:
    print("⚠️  Config not available, using defaults")
    Config = None


class QAIntelligenceTeam:
    """
    QA Intelligence Team - Equipo colaborativo de agentes especializados en QA
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Inicializa el equipo QA Intelligence

        Args:
            config: Configuración del proyecto (opcional)
        """
        self.config = config or self._get_default_config()
        self.model = self._setup_model()
        self.memory = self._setup_memory()
        self.agents = {}
        self.team = None

        # Initialize team
        self._create_specialized_agents()
        self._create_team()

    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto si Config no está disponible"""
        return {
            "model": {"name": "gpt-4o-mini", "temperature": 0.7},
            "database": {"paths": {"conversations": "data/qa_conversations.db"}},
        }

    def _setup_model(self) -> OpenAIChat:
        """Configura el modelo de IA"""
        model_config = self.config.get("model", {})
        return OpenAIChat(
            id=model_config.get("name", "gpt-4o-mini"),
            temperature=model_config.get("temperature", 0.7),
        )

    def _setup_memory(self) -> Memory:
        """Configura el sistema de memoria compartida"""
        # Get database path from config
        if hasattr(self.config, "get_database_config"):
            db_config = self.config.get_database_config()
            db_path = db_config["conversations_path"]
        else:
            db_path = (
                self.config.get("database", {})
                .get("paths", {})
                .get("conversations", "data/qa_conversations.db")
            )

        memory_db = SqliteMemoryDb(table_name="qa_team_memories", db_file=db_path)

        return Memory(
            model=self.model,
            db=memory_db,
            # user_id removed as it may not be supported in this version
            delete_memories=False,
            clear_memories=False,
        )

    def _create_specialized_agents(self):
        """Crea agentes especializados para el equipo QA"""

        # 1. Test Strategy Agent
        self.agents["strategy"] = Agent(
            name="QA Strategy Agent",
            model=self.model,
            memory=self.memory,
            instructions="""
            You are a Senior QA Strategy Expert specialized in:
            
            🎯 CORE EXPERTISE:
            - Test strategy planning and design
            - Risk-based testing approaches
            - Test coverage analysis and optimization
            - Quality metrics definition and tracking
            - Test process improvement
            
            🔍 RESPONSIBILITIES:
            - Analyze requirements and define test strategy
            - Identify testing scope and priorities
            - Recommend test types and approaches
            - Assess project risks and mitigation strategies
            - Define quality gates and acceptance criteria
            
            💡 APPROACH:
            - Think strategically about the big picture
            - Focus on value and ROI of testing efforts
            - Consider project constraints and timelines
            - Provide actionable recommendations
            - Collaborate with automation and analysis agents
            """,
            show_tool_calls=True,
        )

        # 2. Test Automation Agent
        self.agents["automation"] = Agent(
            name="QA Automation Agent",
            model=self.model,
            memory=self.memory,
            instructions="""
            You are a Senior Test Automation Expert specialized in:
            
            🛠️ CORE EXPERTISE:
            - Test automation frameworks (Selenium, Cypress, Playwright, etc.)
            - CI/CD integration and DevOps practices
            - Code quality and maintainability
            - Performance and load testing automation
            - API and service testing
            
            🔧 RESPONSIBILITIES:
            - Design automation architectures and frameworks
            - Recommend tools and technologies
            - Create maintainable test code examples
            - Integrate testing into CI/CD pipelines
            - Optimize test execution and reporting
            
            💻 APPROACH:
            - Focus on practical, implementable solutions
            - Consider maintainability and scalability
            - Provide code examples and best practices
            - Think about the technical implementation
            - Collaborate with strategy and analysis agents
            """,
            show_tool_calls=True,
        )

        # 3. Bug Analysis Agent
        self.agents["analysis"] = Agent(
            name="QA Analysis Agent",
            model=self.model,
            memory=self.memory,
            instructions="""
            You are a Senior QA Analysis Expert specialized in:
            
            🔬 CORE EXPERTISE:
            - Root cause analysis and debugging
            - Bug categorization and prioritization
            - Defect pattern recognition
            - Quality metrics analysis
            - Test results interpretation
            
            📊 RESPONSIBILITIES:
            - Analyze defects and their root causes
            - Identify quality trends and patterns
            - Recommend process improvements
            - Assess testing effectiveness
            - Provide data-driven insights
            
            🎯 APPROACH:
            - Be analytical and detail-oriented
            - Look for patterns and trends
            - Provide evidence-based recommendations
            - Focus on continuous improvement
            - Collaborate with strategy and automation agents
            """,
            show_tool_calls=True,
        )

    def _create_team(self):
        """Crea el equipo colaborativo"""
        self.team = Team(
            name="QA Intelligence Team",
            members=list(self.agents.values()),
            instructions="""
            You are the QA Intelligence Team - a collaborative group of QA experts working together 
            to provide comprehensive testing and quality assurance guidance.
            
            🤝 TEAM COLLABORATION RULES:
            
            1. **Strategy Agent** leads with high-level planning and risk assessment
            2. **Automation Agent** provides technical implementation guidance
            3. **Analysis Agent** offers data-driven insights and quality metrics
            4. **Cross-pollinate ideas** and reference each other's expertise
            5. **Provide unified recommendations** that combine all perspectives
            
            📋 WORKFLOW:
            - Strategy Agent sets the foundation with overall approach
            - Automation Agent details technical implementation
            - Analysis Agent provides metrics and validation approaches
            - All agents collaborate to ensure comprehensive coverage
            
            🎯 OUTPUT GOALS:
            - Comprehensive, actionable QA guidance
            - Multiple perspectives on testing challenges
            - Practical, implementable recommendations
            - Clear next steps and priorities
            """,
            show_tool_calls=True,
        )

    def consult(self, query: str) -> str:
        """
        Consulta al equipo QA sobre un tema específico

        Args:
            query: Pregunta o descripción del problema QA

        Returns:
            Respuesta colaborativa del equipo
        """
        if not self.team:
            raise RuntimeError("Team not initialized")

        try:
            response = self.team.run(query)
            return (
                str(response.content)
                if response and hasattr(response, "content")
                else "No response from team"
            )
        except Exception as e:
            return f"Error en consulta del equipo: {str(e)}"

    def get_team_info(self) -> Dict[str, Any]:
        """Obtiene información del equipo"""
        return {
            "name": self.team.name if self.team else "Not initialized",
            "members": len(self.agents),
            "agents": {
                name: {
                    "name": agent.name,
                    "model": str(agent.model),
                    "memory": bool(agent.memory),
                }
                for name, agent in self.agents.items()
            },
            "memory_enabled": bool(self.memory),
            "initialized": bool(self.team),
        }


def demo_qa_team():
    """Demostración del equipo QA Intelligence"""
    print("🤖 QA Intelligence Team Demo")
    print("=" * 40)

    try:
        # Initialize team
        print("🚀 Initializing QA Intelligence Team...")
        qa_team = QAIntelligenceTeam()

        # Show team info
        team_info = qa_team.get_team_info()
        print(f"\n✅ Team initialized: {team_info['name']}")
        print(f"   Members: {team_info['members']}")
        print(f"   Memory enabled: {team_info['memory_enabled']}")

        # List agents
        print("\n👥 Team Members:")
        for name, info in team_info["agents"].items():
            print(f"   - {info['name']}")

        # Demo consultation (if API key is available)
        print("\n❓ Would you like to test team consultation? (y/n): ", end="")
        if input().lower().startswith("y"):
            demo_query = """
            We're developing a microservices-based e-commerce platform with:
            - 15 microservices
            - React frontend
            - Node.js backend services
            - MongoDB and Redis databases
            - Expected 50,000 daily active users
            - Deployment on AWS with Docker/Kubernetes
            
            We need a comprehensive QA strategy. Can you help us with:
            1. Overall testing strategy and approach
            2. Automation framework recommendations
            3. Key metrics to track and quality gates
            """

            print("\n🔄 Team consultation in progress...")
            try:
                response = qa_team.consult(demo_query)
                print("\n📋 Team Response:")
                print("=" * 50)
                print(response)
            except Exception as e:
                print(f"\n❌ Consultation failed: {e}")
                print("💡 This is likely due to missing OpenAI API key")
        else:
            print("⏭️  Skipping consultation demo")

        print("\n✅ QA Intelligence Team demo complete!")
        return qa_team

    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        return None


if __name__ == "__main__":
    try:
        demo_qa_team()
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
