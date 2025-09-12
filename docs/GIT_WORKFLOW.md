# Git Workflow & Branching Strategy

## 🚫 **What NOT to do** (Lo que hicimos mal hoy):
```bash
# ❌ INCORRECTO - Push directo a develop
git add .
git commit -m "fix: some changes"
git push origin develop  # ¡NO HAGAS ESTO!
```

## ✅ **Correct Git Workflow** (Protocolo correcto):

### 1. **Create Feature Branch**
```bash
# Siempre partir desde develop actualizado
git checkout develop
git pull origin develop

# Crear rama feature con nombre descriptivo
git checkout -b feature/fix-base-url-separation
# Naming convention: feature/description-of-change
```

### 2. **Make Changes & Commit**
```bash
# Hacer cambios y commits
git add .
git commit -m "fix: separate base URL from endpoint paths"

# Push a la rama feature (no a develop)
git push origin feature/fix-base-url-separation
```

### 3. **Create Pull Request**
```bash
# En GitHub/GitLab, crear Pull Request desde:
# feature/fix-base-url-separation → develop

# Incluir:
# - Descripción clara de los cambios
# - Por qué se hizo el cambio
# - Qué se testeo
# - Screenshots si aplica
```

### 4. **Code Review Process**
```bash
# Esperar review y aprobación
# Hacer cambios si se solicitan
# Una vez aprobado, mergear PR
```

### 5. **Cleanup**
```bash
# Después del merge, limpiar rama local
git checkout develop
git pull origin develop
git branch -d feature/fix-base-url-separation
```

## 🏷️ **Branch Naming Convention**

### **Tipos de Ramas:**
- `feature/` - Nuevas funcionalidades
- `fix/` - Bug fixes
- `hotfix/` - Fixes urgentes para producción
- `refactor/` - Refactoring de código
- `docs/` - Documentación
- `test/` - Tests

### **Ejemplos:**
```bash
feature/postman-import-integration
fix/websocket-v2-compatibility  
hotfix/database-connection-timeout
refactor/clean-endpoints-architecture
docs/api-documentation-update
test/endpoint-migration-validation
```

## 🔒 **Branch Protection Rules** (Recomendadas)

Para `develop` branch en GitHub:
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass before merging  
- ✅ Require branches to be up to date before merging
- ✅ Require linear history (rebase/squash merge)
- ❌ Allow force pushes (nunca permitir)

## 📝 **Commit Message Convention**

```bash
# Formato: <type>: <description>
# 
# Types:
feat:     # Nueva funcionalidad
fix:      # Bug fix  
docs:     # Documentación
style:    # Formato, espacios, etc.
refactor: # Refactoring (no cambia funcionalidad)
test:     # Tests
chore:    # Mantenimiento, configuración

# Ejemplos:
feat: add Postman collection import functionality
fix: resolve base URL separation in endpoints  
docs: update API integration guide
refactor: optimize database query patterns
test: add endpoint normalization validation
```

## 🚨 **Emergency Hotfix Process**

Solo para cambios críticos en producción:

```bash
# 1. Partir desde main/master (producción)
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-patch

# 2. Fix rápido
git commit -m "hotfix: resolve security vulnerability"
git push origin hotfix/critical-security-patch

# 3. PR directo a main Y develop
# 4. Deploy inmediato después de merge
```

## 💡 **Lo que deberíamos haber hecho hoy:**

```bash
# Workflow correcto para los cambios de hoy:
git checkout develop
git pull origin develop

# Rama para limpieza de base de datos
git checkout -b feature/database-cleanup-redundant-tables
# ... commits ...
git push origin feature/database-cleanup-redundant-tables
# PR: feature/database-cleanup-redundant-tables → develop

# Rama para separación de base URLs  
git checkout -b fix/separate-base-url-from-endpoints
# ... commits ...
git push origin fix/separate-base-url-from-endpoints  
# PR: fix/separate-base-url-from-endpoints → develop

# Rama para limpieza final de variables
git checkout -b fix/remove-infrastructure-variables-from-paths
# ... commits ...
git push origin fix/remove-infrastructure-variables-from-paths
# PR: fix/remove-infrastructure-variables-from-paths → develop
```

## 🎯 **Benefits of This Approach**

1. **🔍 Code Review**: Otros pueden revisar cambios antes del merge
2. **📝 Documentation**: PRs documentan el por qué de cada cambio  
3. **🧪 Testing**: CI/CD puede correr tests antes del merge
4. **🔄 Rollback**: Fácil revertir cambios específicos si hay problemas
5. **👥 Collaboration**: Múltiples personas pueden trabajar sin conflicts
6. **📊 Traceability**: Historial claro de qué cambió y por qué

## 🚀 **Next Steps**

Para implementar esto en el proyecto:

1. Configurar branch protection rules en GitHub
2. Crear templates de PR  
3. Setup CI/CD pipeline que corra tests en PRs
4. Documentar el workflow en el README
5. Entrenar al equipo en estas prácticas

---

**Remember**: `develop` branch should be protected and never receive direct pushes!