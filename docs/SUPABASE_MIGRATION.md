# Migración de SQLite a Supabase PostgreSQL

Esta guía te ayudará a migrar QA Intelligence de SQLite a Supabase PostgreSQL para resolver los problemas de concurrencia y mejorar el rendimiento.

## ¿Por qué migrar a Supabase?

### Problemas con SQLite

- ❌ **Concurrencia limitada**: Errores "database disk image is malformed"
- ❌ **Bloqueos**: Múltiples servicios (WebSocket, Prometheus) causan conflictos
- ❌ **Escalabilidad**: No adecuado para múltiples procesos simultáneos

### Beneficios de Supabase

- ✅ **Concurrencia robusta**: PostgreSQL maneja múltiples conexiones perfectamente
- ✅ **APIs automáticas**: REST API y GraphQL incluidos
- ✅ **Tiempo real**: Subscripciones en vivo para cambios de datos
- ✅ **Escalabilidad**: Pool de conexiones y clustering automático
- ✅ **Respaldos automáticos**: Sin pérdida de datos
- ✅ **Dashboard web**: Interface visual para administración

## Paso 1: Crear Proyecto Supabase

1. Ve a [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Crea una cuenta (gratis)
3. Haz clic en "New Project"
4. Llena los datos:
   - **Name**: QA Intelligence
   - **Password**: (guarda esta contraseña)
   - **Region**: Elige el más cercano a ti

## Paso 2: Obtener Credenciales

En tu proyecto Supabase:

### Database URL (Settings > Database)

```
postgresql://postgres.[proyecto]:[contraseña]@aws-0-[región].pooler.supabase.com:6543/postgres
```

### API Keys (Settings > API)

- **Project URL**: `https://[proyecto].supabase.co`
- **anon public**: Para aplicaciones cliente
- **service_role**: Para operaciones de backend (úsala)

## Paso 3: Configurar Conexión

1. Copia el archivo de configuración:

```bash
cp .env.supabase .env.supabase.local
```

2. Edita `.env.supabase.local` con tus credenciales reales:

```bash
# Supabase Project Details
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Database Connection 
DATABASE_URL=postgresql://postgres.tu-proyecto:tu-contraseña@aws-0-region.pooler.supabase.com:6543/postgres
```

## Paso 4: Ejecutar Migración

```bash
# Verificar configuración
make check-supabase

# Ejecutar migración completa
make migrate-to-supabase

# Crear tablas en Supabase
make init-supabase-db

# Probar conexión
make test-supabase
```

## Paso 5: Validar Servicios

Después de la migración, verifica que todos los servicios funcionen:

```bash
# Probar QA Agent
make run

# En otra terminal: Probar WebSocket + Prometheus
make run-server

# Verificar que no hay errores de concurrencia
tail -f logs/qa_intelligence.log
```

## Paso 6: Actualizar Producción

Para usar Supabase en producción, actualiza las variables de entorno:

```bash
export DATABASE_URL="postgresql://postgres.proyecto:contraseña@..."
export SUPABASE_URL="https://proyecto.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJ..."
```

## Comandos Útiles

```bash
# Verificar estado de migración
make migrate-to-supabase

# Solo verificar configuración
make check-supabase

# Reinicializar base de datos
make init-supabase-db

# Ver logs de conexión
tail -f logs/qa_intelligence.log | grep -i postgres
```

## Rollback (Si es necesario)

Si necesitas volver a SQLite temporalmente:

```bash
# Renombrar archivo de configuración
mv .env.supabase.local .env.supabase.backup

# Los servicios automáticamente usarán SQLite como fallback
make run
```

## Verificación Final

Después de migrar, deberías ver:

- ✅ Servicios múltiples corriendo sin errores de bloqueo
- ✅ WebSocket server funcionando correctamente  
- ✅ Prometheus metrics sin conflictos de base de datos
- ✅ Imports de Postman funcionando sin corrupción

## Troubleshooting

### Error: "Supabase not configured"

- Verifica que `.env.supabase` exista y tenga las variables correctas
- Asegúrate de que `DATABASE_URL` comience con `postgresql://`

### Error: "Connection failed"

- Verifica que la contraseña sea correcta
- Confirma que el proyecto Supabase esté activo
- Revisa la región en el connection string

### Error: "SSL required"

- Supabase requiere SSL por defecto
- Nuestra configuración ya incluye `sslmode=require`

### Performance lento

- Ajusta `SUPABASE_POOL_SIZE` según tu carga
- Considera usar connection pooling de Supabase (puerto 6543)

## Datos Existentes

⚠️ **Importante**: Esta migración crea un esquema limpio. Los datos de SQLite no se migran automáticamente.

Si necesitas migrar datos específicos:

1. Exporta datos importantes de SQLite
2. Usa los scripts en `scripts/` para importar a Supabase
3. O recrea los datos necesarios usando las APIs existentes

---

¿Necesitas ayuda? Revisa los logs con `make view-logs` o corre `make migrate-to-supabase` para diagnósticos detallados.
