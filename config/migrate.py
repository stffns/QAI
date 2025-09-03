#!/usr/bin/env python3
"""
Migration script to update existing configuration to use Pydantic models
Provides backwards compatibility while transitioning to the new config system
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Settings, get_settings
from config.models import ModelConfig, DatabaseConfig, ToolsConfig


class LegacyConfigManager:
    """
    Legacy ConfigManager wrapper that provides backwards compatibility
    while using the new Pydantic-based configuration system internally
    """
    
    def __init__(self, config_file: str = "agent_config.yaml"):
        """Initialize with legacy interface but use new Settings internally"""
        self._settings = Settings(config_file=config_file)
        self.config_file = config_file
        self._config = self._settings.model_dump()
    
    def get(self, key: str, default=None):
        """Legacy get method using dot notation"""
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value):
        """Legacy set method - updates internal settings"""
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # Update the internal settings object
        self._update_settings_from_dict()
    
    def _update_settings_from_dict(self):
        """Update the internal Settings object from the dict representation"""
        try:
            # Create new settings with updated config - pass config_file separately
            config_data = {k: v for k, v in self._config.items() if k != 'config_file'}
            self._settings = Settings(config_file=self.config_file, **config_data)
        except Exception as e:
            print(f"⚠️  Error updating settings: {e}")
    
    def get_api_key(self) -> str:
        """Get API key using new Settings"""
        return self._settings.get_api_key()
    
    def get_model_config(self):
        """Get model configuration - returns dict for backwards compatibility"""
        return self._settings.get_model_config()
    
    def get_database_config(self):
        """Get database configuration - returns dict for backwards compatibility"""
        return self._settings.get_database_config()
    
    def get_tools_config(self):
        """Get tools configuration - returns dict for backwards compatibility"""
        return self._settings.get_tools_config()
    
    def get_interface_config(self):
        """Get interface configuration - returns dict for backwards compatibility"""
        return self._settings.get_interface_config()
    
    def get_agent_instructions(self):
        """Get agent instructions"""
        return self._settings.get_agent_instructions()
    
    def validate_config(self):
        """Validate configuration using new Pydantic validation"""
        return self._settings.validate_config()
    
    def get_storage_config(self):
        """Get storage configuration for backwards compatibility"""
        return self._settings.get_storage_config()
    
    def save_config(self):
        """Save configuration to YAML file"""
        self._settings.save_config(self.config_file)


# Create a global instance that mimics the old ConfigManager
ConfigManager = LegacyConfigManager


def migrate_existing_config():
    """
    Migration function to help transition from old config to new Pydantic-based config
    """
    print("🔄 Migrating configuration to Pydantic-based system...")
    
    # Check if old config file exists
    old_config_file = "agent_config.yaml"
    if not Path(old_config_file).exists():
        print(f"📁 No existing config file found at {old_config_file}")
        print("✅ Creating new configuration with defaults...")
        
        # Create new configuration with defaults
        settings = Settings()
        settings.save_config(old_config_file)
        print(f"✅ Created new configuration file: {old_config_file}")
        return
    
    try:
        # Load existing config and validate it with new Pydantic models
        print(f"📖 Loading existing configuration from {old_config_file}")
        settings = Settings(config_file=old_config_file)
        
        print("🔍 Validating configuration with Pydantic models...")
        settings.validate_config()
        
        print("✅ Configuration validation successful!")
        print("\n📊 Configuration Summary:")
        summary = settings.summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Save back to ensure any new defaults are added
        backup_file = f"{old_config_file}.backup"
        if not Path(backup_file).exists():
            print(f"💾 Creating backup: {backup_file}")
            import shutil
            shutil.copy2(old_config_file, backup_file)
        
        print(f"💾 Updating configuration file with any new defaults...")
        settings.save_config(old_config_file)
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your environment variables (API keys)")
        print("2. Validate your YAML syntax")
        print("3. Review the configuration requirements")
        return False
    
    return True


def validate_current_config():
    """Validate the current configuration and provide detailed feedback"""
    print("🔍 Validating current configuration...")
    
    try:
        settings = get_settings()
        settings.validate_config()
        
        print("✅ Configuration is valid!")
        print("\n📊 Configuration Details:")
        
        # Model configuration
        model_config = settings.model
        print(f"\n🤖 Model Configuration:")
        print(f"  Provider: {model_config.provider}")
        print(f"  Model ID: {model_config.id}")
        print(f"  Temperature: {model_config.temperature}")
        print(f"  API Key: {'✅ Set' if model_config.api_key else '❌ Missing'}")
        
        # Database configuration
        db_config = settings.database
        print(f"\n🗄️  Database Configuration:")
        print(f"  Main URL: {db_config.url}")
        print(f"  Conversations: {db_config.conversations_path}")
        print(f"  Knowledge: {db_config.knowledge_path}")
        
        # Tools configuration
        tools_config = settings.tools
        print(f"\n🔧 Tools Configuration:")
        print(f"  Enabled: {tools_config.enabled}")
        print(f"  Tools count: {len(tools_config.tools)}")
        for tool in tools_config.tools:
            status = "✅" if tool.enabled else "❌"
            print(f"    {status} {tool.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        print("\n🔧 Suggested fixes:")
        print("1. Run: python -m config.migrate to fix configuration")
        print("2. Check your .env file for required API keys")
        print("3. Review your agent_config.yaml file")
        return False


if __name__ == "__main__":
    """Run migration and validation when executed directly"""
    print("🏗️  QA Intelligence Configuration Migration Tool")
    print("=" * 50)
    
    # Run migration
    migration_success = migrate_existing_config()
    
    if migration_success:
        print("\n" + "=" * 50)
        # Run validation
        validate_current_config()
        
        print("\n" + "=" * 50)
        print("🎉 Configuration system updated successfully!")
        print("\n📝 What's new:")
        print("✅ Type-safe configuration with Pydantic")
        print("✅ Better validation and error messages")
        print("✅ Support for multiple model providers")
        print("✅ Backwards compatibility maintained")
        print("\n🚀 Your application can now use the improved configuration system!")
    else:
        print("\n❌ Migration failed. Please check the errors above and try again.")
        sys.exit(1)
