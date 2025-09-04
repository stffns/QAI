# 🤖 QA Intelligence Chat Agent

**Un agente de chat inteligente especializado en QA Testing e Intelligence con sistema de configuración avanzado y capacidades de reasoning opcional.**

Desarrollado con [Agno 1.8.1](https://github.com/agnoai/agno) con arquitectura modular, Memory v2 y Reasoning Agents.

## ✅ Estado del Proyecto

- ✅ **Arquitectura modular SRP** - Componentes reutilizables y mantenibles
- ✅ **Memory v2 integrado** - Sistema de memoria avanzado de Agno
- ✅ **Reasoning Agents** - Capacidades de razonamiento profundo (opcional)
- ✅ **Sistema de configuración centralizada** - YAML + configurador interactivo
- ✅ **Herramientas integradas** - Python, Calculadora, Web Search
- ✅ **Especialización QA** - Instrucciones y conocimiento enfocado en testing

## 🚀 Inicio Rápido

### **Instalación y Setup**

```bash
# Clonar repositorio
git clone <repository-url>
cd QAI

# Instalar dependencias de desarrollo
make install-dev

# Configurar hooks de git
make setup-hooks

# Validar configuración
make qa-check
```

### **Ejecución principal**

```bash
# Ejecutar el agente QA (Makefile)
make run

# Pasar flags al CLI con ARGS
make run ARGS="--user-id me@qai.com --reasoning agent"

# Ejecutar directamente con Python
python run_qa_agent.py --user-id me@qai.com --reasoning model --reasoning-model-id o3-mini
python run_qa_agent.py --no-memory --reasoning off

# Demo de teams colaborativos
make run-teams

# Validar funcionalidad de teams
make validate-teams
```

### **🧠 Reasoning opcional**

Por defecto el reasoning está **DESHABILITADO** para uso normal. Para habilitar análisis profundo:

```bash
# Editar agent_config.yaml
reasoning:
  enabled: true  # Cambiar a true
  type: "agent"  # "agent", "model", "tools"
```

## 🏗️ Arquitectura Modular

### **Componentes principales**
- **QA Agent**: Coordinador principal (SRP)
- **Model Manager**: Gestión de modelos IA  
- **Tools Manager**: Herramientas disponibles
- **Storage Manager**: Memory v2 con SQLite
- **Chat Interface**: Interfaz conversacional
- **Reasoning Manager**: Capacidades de razonamiento

### **Entry points**
- `run_qa_agent.py` - Agente principal con CLI y flags
- `scripts/run_qa_agent.py` - Wrapper que delega a `run_qa_agent.py`
- `chat_directo.py` - Chat simple cargando `.env`
- `scripts/inspect_memory.py` - Herramienta de inspección de memoria

## 📁 Estructura del Proyecto

```
QAI/
├── 📁 src/           # Código fuente principal
│   ├── agent/        # Agentes y managers
│   ├── core/         # Componentes core
│   └── utils/        # Utilidades
├── 📁 scripts/       # Scripts y herramientas
│   ├── run_qa_agent.py
│   ├── demo_*.py
│   └── inspect_memory.py
├── 📁 docs/          # Documentación
│   ├── README.md
│   └── *.md
├── 📁 data/          # Bases de datos
├── 📁 logs/          # Logs del sistema
├── .env              # Variables de entorno
├── config.py         # Configuración principal
└── agent_config.yaml # Configuración del agente
```

## 🎯 Especialización QA

- ✅ **Mejores prácticas** de QA Testing
- ✅ **Herramientas de testing** y recomendaciones
- ✅ **Estrategias de automatización**
- ✅ **Métricas y KPIs** de calidad
- ✅ **Frameworks de testing** modernos

## 🛠️ Configuración

### **Archivo YAML Principal (`agent_config.yaml`)**

```yaml
# Cambiar modelo fácilmente
model:
  provider: "openai"  # openai, azure, deepseek
  id: "gpt-4"         # gpt-3.5-turbo, gpt-4, gpt-4-turbo
  temperature: 0.7    # 0.0 = determinista, 2.0 = creativo

# Especialización QA
agent:
  instructions:
    - "Eres un experto en QA Testing e Intelligence."
    - "Proporciona ejemplos prácticos y código de pruebas."
    - "Incluye mejores prácticas y herramientas modernas."

# Herramientas disponibles  
tools:
  web_search: true        # Búsqueda en internet
  python_execution: true  # Ejecutar código Python
  calculator: true        # Cálculos matemáticos
  file_operations: false  # Operaciones con archivos
```

### **Configurador Interactivo**

```bash
python configurator.py
```

**Menú del configurador:**
- 🤖 Cambiar modelo de IA
- 🗄️ Configurar bases de datos  
- 🛠️ Habilitar/deshabilitar herramientas
- 📝 Editar instrucciones del agente
- 🖥️ Configurar interfaz
- 💾 Guardar/restaurar configuración

### **CLI Flags Disponibles**

- `--user-id`: contexto de usuario para QA (por defecto `qa_analyst@qai.com`).
- `--reasoning`: `off`, `agent`, `model`, `tools` (override de configuración YAML).
- `--reasoning-model-id`: id del modelo de reasoning cuando `--reasoning=model` (e.g., `o3-mini`).
- `--no-memory`: deshabilita la memoria persistente en la sesión actual.

Ejemplos:

```bash
python run_qa_agent.py --user-id qa_lead@qai.com --reasoning tools
make run ARGS="--no-memory --reasoning off"
```

## 💬 Usando el Agente

### **Comandos Especiales**

- `config` - Ver configuración actual
- `help` - Mostrar ayuda y comandos
- `salir` - Terminar conversación

### **Ejemplo de Conversación**

```
👤 Tú: ¿Cuáles son las mejores prácticas de testing automatizado?

🤖 Agente: Te comparto las mejores prácticas de testing automatizado:

## 1. Estrategia y Planificación
- Usa la pirámide de testing: muchas pruebas unitarias...
- Automatiza casos repetitivos y de regresión...

## 2. Diseño de Pruebas
[Respuesta especializada con ejemplos de código]
```

### **Herramientas Integradas**

```
👤 Tú: Calcula la cobertura de código si tengo 850 líneas cubiertas de 1200 total

🤖 Agente: [Usa calculadora integrada]
Cobertura = (850 / 1200) × 100 = 70.83%

� Tú: Genera un script Python para automatizar pruebas de API

🤖 Agente: [Usa herramientas Python para generar código]
```

## 🗄️ Arquitectura de Datos

### **Bases de Datos Configurables**

```yaml
database:
  # Base principal
  url: "sqlite:///./data/qa_intelligence.db"
  
  # Bases específicas
  paths:
    conversations: "data/chat_conversations.db"  # Historial
    knowledge: "data/agno_knowledge.db"         # Conocimiento
    rag: "data/qa_intelligence_rag.db"          # RAG/Vectorial
```

### **Soporte Multi-BD**

- **SQLite** (por defecto) - Archivos locales
- **PostgreSQL** - Base externa para producción
- **Rutas personalizadas** - Organización flexible

## 🔧 Personalización Avanzada

### **Para Equipos de QA Específicos**

```yaml
agent:
  instructions:
    - "Especialízate en testing de aplicaciones web con React"
    - "Usa Cypress, Jest y Testing Library en ejemplos"
    - "Enfócate en testing de accesibilidad WCAG"

tools:
  web_search: true      # Para buscar documentación
  python_execution: true  # Para scripts de automatización
  file_operations: true   # Para generar archivos de test
```

### **Para Diferentes Modelos**

```yaml
# Configuración económica
model:
  id: "gpt-3.5-turbo"
  temperature: 0.3  # Más determinista

# Configuración premium  
model:
  id: "gpt-4"
  temperature: 0.7  # Más creativo

# Azure corporativo
model:
  provider: "azure"
  id: "gpt-4-deployment"
```

## 📊 Verificación y Monitoreo

### **Ver Estado Actual**

```bash
python config.py
```

**Salida ejemplo:**
```
📋 Configuración Actual
==================================================
🤖 Modelo: openai / gpt-4
🌡️ Temperatura: 0.7
🔑 API Key: ✅ Configurada

🛠️ Herramientas:
   python_execution: ✅
   calculator: ✅
   web_search: ⚠️ (en desarrollo)

🖥️ Interfaz:
   Markdown: ✅
   Tool calls: ✅
==================================================
```

## 🚀 Ventajas del Agente Único

✅ **Simplicidad** - Una sola implementación que hacer funcionar  
✅ **Completitud** - Todas las funcionalidades integradas  
✅ **Mantenibilidad** - Fácil de actualizar y extender  
✅ **Configurabilidad** - Adaptable a cualquier necesidad  
✅ **Especialización** - Enfocado en QA desde el inicio  
✅ **Escalabilidad** - Configuración para desarrollo y producción  

## 📚 Recursos

- [Documentación de Agno](https://docs.agno.ai/)
- [OpenAI Models](https://platform.openai.com/docs/models)
- [YAML Tutorial](https://yaml.org/spec/1.2.2/)
- [QA Testing Best Practices](https://agilealliance.org/agile101/testing/)

---

## 🎯 Próximos Pasos Recomendados

1. **Configurar para tu equipo** → `python configurator.py`
2. **Probar funcionalidades** → `python chat_agent.py`
3. **Personalizar instrucciones** → Editar `agent_config.yaml`
4. **Integrar en workflow** → Usar en proyectos de QA

**¡Tu agente especializado en QA está listo para usar! 🎉**

## 🚀 Inicio Rápido

### 1. Activar el entorno (si no está activo)

```bash
source .venv/bin/activate
```

### 2. Ejecutar demo rápido

```bash
python demo_agent.py
```

### 3. Chat interactivo simple

```bash
python chat_agent.py
```

### 4. Chat avanzado con herramientas

```bash
python advanced_chat_agent.py
```

## 🤖 Agentes Disponibles

### 1. Demo Agent (`demo_agent.py`)

Demostración rápida con preguntas predefinidas.

**Características:**
- Prueba automática del agente
- Preguntas de ejemplo
- Verificación de funcionamiento

### 2. Chat Agent Simple (`chat_agent.py`)

Un agente básico de conversación con GPT-3.5-turbo.

**Características:**
- ✅ Conversación simple con IA
- ✅ Interfaz de línea de comandos
- ✅ Respuestas en markdown
- ✅ Memoria de conversación

**Comandos:**
- Escribe cualquier mensaje para conversar
- `salir`, `quit`, `exit` - Terminar conversación

### 3. Advanced Chat Agent (`advanced_chat_agent.py`)

Un agente avanzado con herramientas y capacidades extendidas.

**Características:**
- 🔍 Búsqueda en internet con DuckDuckGo
- 🐍 Ejecución de código Python
- 💾 Memoria persistente de conversaciones
- 🌐 Interfaz web opcional (Playground)

**Comandos especiales:**
- `salir` - Terminar conversación
- `nuevo` - Iniciar nueva conversación
- `playground` - Abrir interfaz web en <http://localhost:7777>

## 📝 Ejemplos de Uso

### Demo Rápido

```bash
$ python demo_agent.py
🚀 Demo del Agente de Chat con Agno
========================================

📝 Pregunta 1: ¿Qué es la inteligencia artificial?
🤖 Respuesta: La inteligencia artificial es una disciplina...
```

### Chat Simple

```text
👤 Tú: Hola, ¿cómo estás?
🤖 Agente: ¡Hola! Estoy muy bien, gracias por preguntar...
```

### Chat Avanzado con Herramientas

```text
👤 Tú: ¿Cuál es el clima actual en Madrid?
🤖 Agente: Voy a buscar información sobre el clima actual en Madrid...
[Usa DuckDuckGo para buscar información actualizada]

👤 Tú: Calcula la raíz cuadrada de 144
🤖 Agente: Voy a calcular eso usando Python...
[Ejecuta código Python para calcular el resultado]
```

## 🛠️ Configuración

### Dependencias Instaladas

```text
agno==1.8.1
python-dotenv
openai
duckduckgo-search
fastapi
uvicorn
```

### Variables de Entorno

El archivo `.env` ya está configurado con:

```env
OPENAI_API_KEY=sk-proj-O2K8...
```

## 🗄️ Base de Datos

El agente avanzado crea automáticamente:
- `data/chat_conversations.db` - Para almacenar conversaciones

## 🎯 Próximos Pasos

1. **Personalizar el agente** - Modifica las instrucciones en los archivos
2. **Agregar herramientas** - Explora más herramientas de agno
3. **Interfaz web** - Usa el comando `playground` en el agente avanzado
4. **Integrar con tu proyecto** - Usa los agentes en tus aplicaciones

## 🔧 Personalización

### Cambiar el Modelo

```python
model = OpenAIChat(
    id="gpt-4",  # Cambiar a gpt-4 para mejor calidad
    api_key=api_key
)
```

### Personalizar Instrucciones

```python
instructions=[
    "Eres un experto en [tu dominio]",
    "Siempre proporciona ejemplos prácticos",
    # Agrega tus instrucciones personalizadas
]
```

## 📚 Recursos

- [Documentación de Agno](https://docs.agno.ai/)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/)

## ✨ Creado con

- **Agno 1.8.1** - Framework de agentes de IA
- **OpenAI GPT-3.5-turbo** - Modelo de lenguaje
- **Python 3.13** - Lenguaje de programación
