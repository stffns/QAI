# Estrategia de Ramas - QA Intelligence

## Flujo de Trabajo por Tareas

A partir de ahora, seguiremos una estrategia de desarrollo basada en ramas por tareas para mantener el código organizado y funcional.

### Ramas Principales

- **`main`**: Producción (código estable y probado)
- **`develop`**: Desarrollo principal (integración de features)
- **`feature/*`**: Nuevas funcionalidades
- **`fix/*`**: Correcciones de errores
- **`hotfix/*`**: Correcciones urgentes en producción

### Nomenclatura de Ramas

```bash
# Nuevas funcionalidades
feature/websocket-authentication
feature/advanced-memory-system
feature/custom-tools-integration

# Correcciones
fix/streaming-timeout-issue
fix/model-selection-bug

# Mejoras
enhancement/response-optimization
enhancement/logging-improvements

# Experimentos
experiment/new-model-provider
experiment/performance-testing
```

### Flujo de Trabajo

#### 1. Crear Nueva Rama para Tarea
```bash
# Desde develop, crear nueva rama
git checkout develop
git pull origin develop
git checkout -b feature/nombre-de-la-tarea

# Ejemplo:
git checkout -b feature/add-user-authentication
```

#### 2. Desarrollar en la Rama
```bash
# Hacer commits frecuentes y descriptivos
git add .
git commit -m "feat: implement user authentication system"

# Push de la rama
git push -u origin feature/add-user-authentication
```

#### 3. Merge a Develop
```bash
# Volver a develop
git checkout develop
git pull origin develop

# Merge de la feature
git merge feature/add-user-authentication
git push origin develop

# Eliminar rama local (opcional)
git branch -d feature/add-user-authentication
```

### Reglas de Desarrollo

1. **Nunca hacer commits directos a `develop`** sin rama de feature
2. **Siempre probar** antes de hacer merge
3. **Commits descriptivos** siguiendo conventional commits
4. **Una tarea = Una rama** (mantener scope pequeño)
5. **Verificar WebSocket funcionando** antes de cada merge

### Plantilla de Commits

```
tipo: descripción breve

🎯 Cambios principales:
- Lista de cambios importantes
- Funcionalidades agregadas
- Mejoras implementadas

🔧 Detalles técnicos:
- Archivos modificados
- Configuraciones actualizadas
- Integraciones añadidas

✅ Validaciones:
- Tests pasando
- WebSocket funcionando
- Configuración validada
```

### Comandos Útiles

```bash
# Ver todas las ramas
git branch -a

# Ver estado de ramas remotas
git remote show origin

# Limpiar ramas eliminadas remotamente
git remote prune origin

# Ver diferencias entre ramas
git diff develop..feature/mi-rama

# Verificar que no hay cambios sin commitear
git status --porcelain
```

### Integración Continua

Antes de cada merge a `develop`:

1. ✅ Verificar WebSocket server funcionando
2. ✅ Validar configuración con `python config.py`
3. ✅ Ejecutar tests básicos
4. ✅ Confirmar Response Manager funcionando
5. ✅ No hay errores en logs

### Ejemplo Práctico

```bash
# Empezar nueva tarea: Agregar autenticación JWT
git checkout develop
git pull origin develop
git checkout -b feature/jwt-authentication

# Desarrollar...
git add .
git commit -m "feat: add JWT authentication middleware"
git push -u origin feature/jwt-authentication

# Probar WebSocket funcional
# Validar configuración
# Hacer merge

git checkout develop
git merge feature/jwt-authentication
git push origin develop
git branch -d feature/jwt-authentication
```

Este flujo asegura que `develop` siempre mantenga el WebSocket funcional y las nuevas features no rompan el sistema base.
