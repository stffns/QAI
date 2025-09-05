# 🧪 Workflow Test Documentation

Este archivo demuestra el workflow de desarrollo configurado para QA Intelligence.

## 📋 Proceso de Desarrollo

### 1. Crear Feature Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/nombre-descriptivo
```

### 2. Desarrollar Feature
- Hacer cambios necesarios
- Escribir tests si es necesario
- Verificar que pasan las pruebas locales

### 3. Commit y Push
```bash
git add .
git commit -m "feat(scope): descripción clara del cambio"
git push -u origin feature/nombre-descriptivo
```

### 4. Crear Pull Request
- Ir a GitHub
- Crear PR desde `feature/nombre-descriptivo` → `develop`
- Usar el template de PR automático
- Completar todos los checks necesarios

### 5. Revisión y Merge
- Esperar revisión de código
- Atender comentarios si los hay
- Merge cuando esté aprobado
- La rama se borra automáticamente

### 6. Deploy a Producción
- Crear PR desde `develop` → `main`
- Revisión más rigurosa
- Merge para deploy a producción

## ✅ Protecciones Configuradas

- **main**: Requires PR reviews, admin enforcement
- **develop**: Basic protection against force pushes
- **GitHub Actions**: Automatic CI/CD on each PR
- **Templates**: Consistent structure for PRs and issues

## 🤖 Automatización QA

El CI/CD incluye:
- Tests de múltiples versiones de Python
- Linting y formateo automático
- Type checking con mypy
- Security scanning
- Tests específicos de WebSocket
- Validación del QA Agent

Esta configuración asegura calidad y consistencia en todo el desarrollo.
