#!/bin/bash
# Script de inicio para el Agente de Chat QA Intelligence

echo "🤖 QA Intelligence Chat Agent"
echo "=============================="

# Verificar si el entorno virtual existe
if [ ! -d ".venv" ]; then
    echo "❌ Error: Entorno virtual no encontrado"
    echo "Por favor, ejecuta este script desde el directorio del proyecto"
    exit 1
fi

# Activar entorno virtual
source .venv/bin/activate

echo "✅ Entorno virtual activado"

# Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "❌ Error: Archivo .env no encontrado"
    exit 1
fi

echo "✅ Configuración encontrada"

# Menú de opciones
echo ""
echo "Selecciona una opción:"
echo "1. 🤖 Iniciar QA Agent (modular)"
echo "2. 📊 Ver configuración actual"
echo "3. 🔍 Verificar instalación"
echo "4. ❌ Salir"

read -p "Opción (1-4): " choice

case $choice in
    1)
        echo "🤖 Iniciando QA Agent modular..."
        python run_qa_agent.py
        ;;
    2)
        echo "📊 Mostrando configuración..."
        python config.py
        ;;
    3)
        echo "📊 Mostrando configuración..."
        python config.py
        ;;
        echo "🔍 Verificando instalación..."
        python -c "
from agno.agent import Agent
from agno.models.openai import OpenAIChat
import os
from dotenv import load_dotenv
load_dotenv()
print('✅ Agno importado correctamente')
print('✅ OpenAI configurado:', 'Sí' if os.getenv('OPENAI_API_KEY') else 'No')
print('✅ Configuración YAML:', 'Sí' if os.path.exists('agent_config.yaml') else 'No')
print('✅ Todo listo para usar!')
"
        ;;
    4)
        echo "👋 ¡Hasta luego!"
        ;;
    *)
        echo "❌ Opción inválida"
        ;;
esac