# QA Intelligence Agent 🤖

Intelligent chat system with modular architecture and advanced capabilities for QA analysis and testing.

## 📋 Overview

The QA Intelligence Agent is a conversational chat system that combines:

- **Persistent memory** with SQLite
- **Specialized tools** (Python, data analysis)
- **Modular SOLID architecture**
- **OpenAI GPT-4 integration**

## 🚀 Available Scripts

### 1. `chat_directo.py` (Recommended)

**Main script for direct chat usage**

```bash
python chat_directo.py
```

**Features:**

- ✅ Simplified initialization
- ✅ Automatic persistent memory
- ✅ Integrated tools
- ✅ Robust error handling

### 2. `qa_agent.py`

**Main agent module (for development)**

```bash
python qa_agent.py
```

**Advanced usage:**

- For integration into other systems
- Development and debugging
- Custom configuration

## ⚙️ Required Configuration

### Environment Variables

Create `.env` file in project root:

```env
OPENAI_API_KEY=sk-proj-your-key-here
```

### YAML Configuration (Optional)

The system uses `agent_config.yaml` for advanced configuration:

```yaml
model:
  provider: "openai"
  id: "gpt-4"
  temperature: 0.7
  max_tokens: 4000

database:
  url: "sqlite:///./data/qa_intelligence.db"
  paths:
    conversations: "data/qa_conversations.db"
    knowledge: "data/agno_knowledge.db"

tools:
  web_search: true
  python_execution: true
  memory_enabled: true
```

## 🛠️ Capabilities and Tools

### 1. Persistent Memory

- **Type:** SQLite with Memory v2
- **Location:** `data/qa_conversations.db`
- **Function:** Remembers conversations between sessions

### 2. Python Execution

- **Status:** ✅ Active
- **Capabilities:**
  - Data analysis
  - Mathematical calculations
  - Graph generation
  - File manipulation

### 3. Web Search

- **Status:** ⚠️ Limited (DuckDuckGo issue)
- **Alternatives:** Can use Python for basic scraping

### 4. QA Analysis

- Testing reports
- Performance analysis
- Test case management
- Database integration

## 🏗️ Modular Architecture

### Managers

#### ModelManager

```python
# Manages AI models
- OpenAI configuration
- Parameter validation
- Factory pattern for multiple providers
```

#### ToolsManager

```python
# Manages available tools
- Python execution
- Web search (limited)
- Custom tools
```

#### StorageManager

```python
# Manages memory and persistence
- Memory v2 with SQLite
- Automatic configuration
- Error handling
```

### Implemented SOLID Patterns

- **S**ingle Responsibility: Each manager has one responsibility
- **O**pen/Closed: Extensible without modifying existing code
- **L**iskov Substitution: Interchangeable managers
- **I**nterface Segregation: Specific interfaces
- **D**ependency Inversion: Dependency injection

## 🔧 Usage and Examples

### Quick Start

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your API key

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Run chat
python chat_directo.py
```

### Conversation Example

```
🙋 Question: Analyze this testing data
🤖 Response: I can help you with the analysis. Could you share the data?

🙋 Question: Calculate the average of [1,2,3,4,5]
🤖 Response: [Executes Python] The average is 3.0

🙋 Question: Do you remember what we talked about before?
🤖 Response: Yes, we were analyzing testing data...
```

## 🐛 Troubleshooting

### Common Issues

#### 1. API Key Error

```
❌ Error: OpenAI API key not found
```

**Solution:** Check `.env` file and `OPENAI_API_KEY` variable

#### 2. Database Error

```
❌ Error: Cannot connect to database
```

**Solution:** Check permissions in `data/` folder

#### 3. DuckDuckGo Warning

```
⚠️ Web search tool not available
```

**Solution:** Doesn't affect main functionality, use Python for searches

#### 4. Type Hints Error

```
⚠️ ConfigValidator | Settings cannot be assigned
```

**Solution:** Just a warning, doesn't affect execution

### Diagnostic Commands

```bash
# Check configuration
python config.py

# Run tests
python -m pytest tests/ -v

# View detailed logs
python chat_directo.py --debug
```

## 📊 System Status

### Tests

- ✅ **21/21 tests passing**
- ✅ SOLID repositories working
- ✅ Database migration successful

### Features

- ✅ Conversational chat
- ✅ Persistent memory
- ✅ Python execution
- ✅ Modular architecture
- ⚠️ Web search (limited)

## 🔄 Data Flow

```text
User → chat_directo.py → QAAgent → 
    ├── ModelManager → OpenAI API
    ├── ToolsManager → Python/Tools
    ├── StorageManager → SQLite Memory
    └── Response → User
```

## 📈 Future Improvements

1. **Web Search:** Implement DuckDuckGo alternative
2. **QA Tools:** More testing-specific tools
3. **Web UI:** Web interface for chat
4. **APIs:** REST endpoints for integration
5. **Plugins:** Extensible plugin system

## 🤝 Contributing

To contribute to the project:

1. Run tests: `pytest tests/ -v`
2. Follow existing SOLID patterns
3. Document new features
4. Maintain compatibility with current configuration

---

**Last update:** September 2025  
**Version:** 1.0.0  
**Status:** Production ready ✅
