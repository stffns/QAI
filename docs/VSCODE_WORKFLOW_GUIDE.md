# VS Code Workflow Guide - QA Intelligence

## Resumen Ejecutivo

Hemos implementado un flujo de desarrollo completo en VS Code para QA Intelligence con **17 tasks especializadas**, **7 configuraciones de debug**, y configuraciones automáticas que transforman tu experiencia de desarrollo.

## 🚀 Acceso Rápido a Tasks

### Método Principal
1. **Ctrl+Shift+P** (Cmd+Shift+P en Mac)
2. Escribir: `Tasks: Run Task`
3. Seleccionar la task deseada

### Método Alternativo
- **Terminal → Run Task** desde el menú de VS Code

## 📋 Tasks Disponibles

### 🤖 Agent Operations
| Task | Descripción | Uso |
|------|-------------|-----|
| **Start QA Agent** | Iniciar agente principal | Desarrollo normal |
| **Start QA Agent (Streaming)** | Iniciar con streaming activado | Demo de streaming |
| **Demo Builder Pattern** | Demostración de mejoras arquitectónicas | Testing de patterns |
| **Emergency Agent Reset** | Reset completo del agente | Resolución de problemas |

### 🎨 Code Quality
| Task | Descripción | Uso |
|------|-------------|-----|
| **Format Code (Black)** | Formatear código Python | Antes de commits |
| **Sort Imports (isort)** | Organizar imports | Limpieza de código |
| **Format & Sort (Black + isort)** | Formateo completo | Preparación final |
| **Lint (Flake8)** | Verificar estilo de código | Control de calidad |
| **Type Check (mypy)** | Verificar tipos estáticos | Validación de tipos |
| **QA Check (Full)** | Pipeline completo de calidad | Antes de deploy |

### 🧪 Testing
| Task | Descripción | Uso |
|------|-------------|-----|
| **Run Tests** | Ejecutar suite de pruebas | Testing rápido |
| **Run Tests (Coverage)** | Pruebas con reporte de cobertura | Análisis profundo |

### ⚙️ Project Utilities
| Task | Descripción | Uso |
|------|-------------|-----|
| **Validate Config** | Validar configuración actual | Diagnóstico |
| **Clean Cache** | Limpiar archivos temporales | Mantenimiento |
| **Database Status** | Estado de bases de datos | Monitoreo |
| **Project Info** | Información del proyecto | Overview técnico |
| **Install Dependencies** | Instalar dependencias | Setup inicial |

## 🐛 Debugging Configurations

### Configuraciones Disponibles
1. **QA Agent Debug** - Debug del agente principal
2. **QA Agent Streaming Debug** - Debug con streaming
3. **Builder Pattern Debug** - Debug del Builder
4. **Config Validation Debug** - Debug de configuración
5. **Current File Debug** - Debug del archivo actual
6. **Python Debug Console** - Consola interactiva
7. **Python Debug with Args** - Debug con argumentos

### Uso de Debug
- **F5** - Iniciar debug del archivo actual
- **Ctrl+Shift+D** - Abrir panel de Debug
- **F9** - Toggle breakpoint
- **F10** - Step over
- **F11** - Step into

## ⚙️ Configuraciones Automáticas

### Formateo Automático
- **Black** se ejecuta automáticamente al guardar
- **isort** organiza imports al guardar
- Configuración en `.vscode/settings.json`

### Linting Integrado
- **Flake8** para estilo de código
- **mypy** para type checking
- **Pylance** para análisis avanzado

### Python Environment
- Virtual environment `.venv` configurado automáticamente
- Interpreter seleccionado automáticamente
- PYTHONPATH configurado para el proyecto

## 📊 Monitoreo de Proyecto

### Estado Actual (Ejemplo)
```
🤖 Modelo: openai / gpt-5-mini
🌡️ Temperatura: 1.0
🔑 API Key: ✅ Configurada

🗄️ Bases de Datos:
   qa_conversations.db: 1.9MB
   qa_intelligence.db: 561KB
   qa_intelligence_rag.db: 307KB
   chat_conversations.db: 16KB

📊 Líneas de código: 6,706
🐍 Python: 3.13.2
```

## 🔄 Flujo de Desarrollo Recomendado

### 1. Inicio de Sesión
```
1. Abrir VS Code en la carpeta del proyecto
2. Ctrl+Shift+P → "Tasks: Run Task" → "Validate Config"
3. Verificar que todo está configurado correctamente
```

### 2. Desarrollo Activo
```
1. Escribir código (formateo automático activado)
2. F5 para debug cuando sea necesario
3. Ctrl+Shift+P → "Tasks: Run Task" → "Run Tests" para validar
```

### 3. Pre-Commit
```
1. Ctrl+Shift+P → "Tasks: Run Task" → "QA Check (Full)"
2. Verificar que todos los checks pasan
3. Commit los cambios
```

### 4. Testing de Agent
```
1. Ctrl+Shift+P → "Tasks: Run Task" → "Start QA Agent"
2. O "Start QA Agent (Streaming)" para testing avanzado
3. "Demo Builder Pattern" para validar mejoras
```

## 🛠️ Resolución de Problemas

### Problemas Comunes

#### Environment no encontrado
```bash
# Solución
Ctrl+Shift+P → "Python: Select Interpreter" → Seleccionar .venv
```

#### Tasks no aparecen
```bash
# Verificar que existe .vscode/tasks.json
# Recargar VS Code: Ctrl+Shift+P → "Developer: Reload Window"
```

#### Debug no funciona
```bash
# Verificar .vscode/launch.json
# Instalar extensión Python
Ctrl+Shift+P → "Extensions: Install Extensions" → "Python"
```

#### Formateo no automático
```bash
# Verificar .vscode/settings.json
# Instalar Black: pip install black
```

### Reset de Emergencia
```
Ctrl+Shift+P → "Tasks: Run Task" → "Emergency Agent Reset"
```

## 📦 Extensiones Recomendadas

Las siguientes extensiones se instalan automáticamente:
- **Python** - Soporte completo para Python
- **Pylance** - Language server avanzado
- **Python Debugger** - Debug integrado
- **autoDocstring** - Generación automática de docstrings
- **GitLens** - Git integrado mejorado
- **Error Lens** - Visualización de errores inline

## 🎯 Próximos Pasos

### Para Desarrolladores
1. Familiarizarse con las tasks más usadas
2. Configurar shortcuts personalizados si es necesario
3. Usar debug activamente durante desarrollo

### Para el Proyecto
1. Las mejoras arquitectónicas están 100% implementadas
2. Streaming mode totalmente funcional
3. Error recovery system operativo
4. Builder pattern en producción

## 🔗 Enlaces Útiles

- **Demo Script**: `python demo_vscode_tasks.py`
- **Config Validation**: `python config.py`
- **Architectural Demo**: `python demo_architectural_improvements.py`
- **Project Documentation**: `docs/` folder

---

## ✅ Estado de Implementación

| Componente | Estado | Descripción |
|------------|--------|-------------|
| **VS Code Tasks** | ✅ 100% | 17 tasks implementadas y probadas |
| **Debug Configs** | ✅ 100% | 7 configuraciones de debug |
| **Auto Settings** | ✅ 100% | Formateo, linting, environment |
| **Builder Pattern** | ✅ 100% | Patrón implementado y funcional |
| **Error Recovery** | ✅ 100% | Sistema de recuperación robusto |
| **Streaming Mode** | ✅ 100% | Streaming completamente funcional |
| **Tool Management** | ✅ 100% | Gestión avanzada de herramientas |

**Resultado Final**: Flujo de desarrollo empresarial completo y funcional para QA Intelligence.
