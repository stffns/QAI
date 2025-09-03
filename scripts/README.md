# 🛠️ Scripts and Tools

Esta carpeta contiene scripts, herramientas de desarrollo y archivos de demostración para el proyecto QA Intelligence.

## 📁 Contenido

### Scripts de Demo
- `demo_advanced_memory.py` - Demostración del sistema de memoria avanzada Memory v2
- `demo_qa_intelligence.py` - Demo principal del QA Intelligence Agent
- `demo_qa_teams_integration.py` - Demo de QA Intelligence con Teams colaborativos

### Scripts de Ejecución
- `run_qa_agent.py` - Script principal para ejecutar el agente QA
- `start.sh` - Script de inicio rápido del sistema

### Herramientas de Desarrollo
- `inspect_memory.py` - Herramienta para inspeccionar y analizar la base de datos de memoria
- `test_reasoning.py` - Script de pruebas para validar el sistema de razonamiento
- `validate_agno_teams.py` - Validación de las capacidades de agno.team.Team
- `qa_intelligence_team.py` - Implementación del QA Intelligence Team colaborativo

## 🚀 Cómo usar los scripts

### Ejecutar el agente QA:
```bash
cd scripts
python run_qa_agent.py
```

### Inspeccionar memoria:
```bash
cd scripts
python inspect_memory.py
```

### Demos:
```bash
cd scripts
python demo_qa_intelligence.py
python demo_advanced_memory.py
python demo_qa_teams_integration.py
```

### Teams & Collaboration:
```bash
cd scripts
# Validar capacidades de Teams
python validate_agno_teams.py

# QA Intelligence Team interactivo
python demo_qa_teams_integration.py

# Ejecutar ejemplos de Teams
python demo_qa_teams_integration.py --examples
```

### Inicio rápido:
```bash
cd scripts
./start.sh
```

## 🔧 Scripts de Utilidad

- **inspect_memory.py**: Permite explorar el contenido de la base de datos qa_conversations.db
- **test_reasoning.py**: Valida que el sistema de razonamiento funcione correctamente
- **Demo scripts**: Muestran las capacidades del sistema de forma interactiva

## 📋 Notas

- Todos los scripts deben ejecutarse desde la carpeta `scripts/`
- Asegúrate de que el entorno virtual esté activado antes de ejecutar los scripts
- Los scripts de demo incluyen ejemplos de uso práctico del sistema
