"""
Storage Manager - Handles storage configuration and connection
"""


# SRP: This class has a single responsibility - managing conversation storage.
# It handles storage setup, configuration, and provides a clean interface
# for storage operations without mixing concerns with models or tools.
class StorageManager:
    """Manages conversation storage configuration and connection"""

    def __init__(self, config):
        """
        Initialize the storage manager with configuration

        Args:
            config: System configuration object
        """
        self.config = config
        self.storage = None

    def setup_storage(self):
        """
        Configure storage according to configuration using Memory v2
        Conecta específicamente a qa_conversations.db desde .env

        Returns:
            Memory instance or None if not available
        """
        db_config = self.config.get_database_config()

        try:
            from agno.memory.v2.db.sqlite import SqliteMemoryDb
            from agno.memory.v2.memory import Memory
            from agno.models.openai import OpenAIChat

            # Usar la base de datos qa_conversations.db del .env
            db_path = db_config["conversations_path"]  # data/qa_conversations.db

            # Create SQLite database for memory
            memory_db = SqliteMemoryDb(
                table_name="qa_user_memories",  # Tabla específica para memorias de usuario
                db_file=db_path,
            )

            # Initialize Memory with model for agentic operations
            self.storage = Memory(
                model=OpenAIChat(id="gpt-4o-mini"),  # Modelo económico para memorias
                db=memory_db,
                delete_memories=True,  # Permite gestión completa
                clear_memories=True,  # Permite limpiar memorias
            )
            print(f"✅ QA Intelligence Memory (v2) connected to: {db_path}")

        except (ImportError, AttributeError) as e:
            print(f"⚠️  Memory: using temporary memory ({e})")
            self.storage = None

        return self.storage

    def get_storage_info(self):
        """
        Get storage information

        Returns:
            dict: Storage information
        """
        db_config = self.config.get_database_config()
        return {
            "enabled": self.storage is not None,
            "type": "Memory v2 (SQLite)" if self.storage else "Temporary Memory",
            "path": (
                db_config.get("conversations_path", "N/A") if self.storage else "N/A"
            ),
        }
