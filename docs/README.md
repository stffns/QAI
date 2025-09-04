# 📚 Documentation

Esta carpeta contiene toda la documentación del proyecto QA Intelligence.

## 📋 Archivos de Documentación

### Core Documentation
- `MEMORY_CONNECTION_SUCCESS.md` - Documentación completa de la implementación exitosa del sistema de memoria conectado a qa_conversations.db
- `ADVANCED_MEMORY_RESULTS.md` - Resultados y análisis del sistema de memoria avanzada Memory v2
- `MEMORY_ANALYSIS.md` - Análisis detallado del funcionamiento de la memoria persistente
- `REASONING_VALIDATION.md` - Validación del sistema de razonamiento del agente QA

## 🎯 Propósito

Esta documentación cubre:
- ✅ Implementación del sistema de memoria
- ✅ Configuración de base de datos
- ✅ Validación de funcionalidades
- ✅ Análisis de rendimiento
- ✅ Guías de uso y configuración

## 📖 Cómo usar esta documentación

1. **Para entender el sistema de memoria**: Leer `MEMORY_CONNECTION_SUCCESS.md`
2. **Para análisis técnico**: Revisar `ADVANCED_MEMORY_RESULTS.md`
3. **Para validación de razonamiento**: Consultar `REASONING_VALIDATION.md`
4. **Para análisis de datos**: Ver `MEMORY_ANALYSIS.md`

## 🚀 Ejecución Rápida (CLI)

Puedes ejecutar el agente desde el wrapper de `scripts/` o directamente desde el entrypoint principal del repositorio.

```bash
# Makefile (recomendado para desarrollo)
make run

# Pasar flags con ARGS
make run ARGS="--user-id me@qai.com --reasoning agent"

# Ejecución directa
python run_qa_agent.py --user-id me@qai.com --reasoning model --reasoning-model-id o3-mini
python run_qa_agent.py --no-memory --reasoning off
```

## ⚙️ Flags Disponibles (CLI)

- `--user-id`: contexto de usuario en memoria (por defecto `qa_analyst@qai.com`).
- `--reasoning`: `off`, `agent`, `model`, `tools` (override de `agent_config.yaml`).
- `--reasoning-model-id`: id del modelo de razonamiento cuando `--reasoning=model` (p. ej., `o3-mini`).
- `--no-memory`: deshabilita memoria persistente en la sesión actual.

## 🧭 Recomendaciones por Entorno

| Entorno       | Memoria | Reasoning         | Herramientas sensibles    | Logging                   |
|---------------|---------|-------------------|---------------------------|---------------------------|
| Desarrollo    | ON      | agent/tools       | Python ON, Files opcional | Console DEBUG + archivos |
| Staging       | ON      | agent             | Python OFF, Files OFF     | INFO + performance log    |
| Producción    | ON/limitada | off/agent (según caso) | Python OFF, Files OFF     | INFO/ERROR, rotación      |

Sugerencias:
- Producción: deshabilitar `file_operations` y ejecución Python; revisar `environment.name` en `agent_config.yaml` y aplicar políticas en el arranque.
- Staging: mantener memoria y razonamiento básico para validar flujos, sin herramientas peligrosas.
- Desarrollo: activar reasoning y Python para generar prototipos y diagnósticos rápidos.

## 🔐 Notas de Seguridad

- Mantén `OPENAI_API_KEY` y credenciales solo en `.env` (no commitear).
- En entornos productivos, usar rutas de datos separadas (volúmenes/paths dedicados).
- Revisa periódicamente los logs de `logs/errors.log` y `logs/performance.log`.
