# Auth JWT — Guía de Verificación

## ✅ Archivos Creados/Modificados

### Nuevos
- `usuarios/serializers.py` — CustomTokenObtainPairSerializer (validación de usuario activo + rol)
- `usuarios/auth_views.py` — CustomTokenObtainPairView + CustomTokenRefreshView

### Modificados
- `config/urls.py` — agregados endpoints `/api/token/` y `/api/token/refresh/` + Swagger docs

### Sin cambios (ya OK)
- `config/settings.py` — JWTAuthentication ya configurado en REST_FRAMEWORK

---

## 🚀 Pasos para Verificar

### 1. Activar venv e instalar dependencias (si no está hecho)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Instalar/actualizar
pip install -r requirements.txt
```

### 2. Verificar Django
```bash
python manage.py check
```
Debe decir: `System check identified no issues (0 silenced).`

### 3. Aplicar migraciones (si falta)
```bash
python manage.py migrate
```

### 4. Crear superusuario (si no existe)
```bash
python manage.py createsuperuser
# Username: testuser
# Password: testpass123
```

### 5. Iniciar servidor
```bash
python manage.py runserver
```
El servidor corre en `http://localhost:8000/`

---

## 📡 Endpoints de Autenticación

### **POST `/api/token/`** — Login
Obtiene access token + refresh token

**Request:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "rol": "admin",
  "user_id": 1
}
```

**Error (401):**
```json
{
  "detail": "No active account found with the given credentials"
}
```

### **POST `/api/token/refresh/`** — Renovar Token
Usa el refresh token para obtener un nuevo access token

**Request:**
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}'
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## 📚 Documentación Automática

Swagger UI se genera automáticamente:
- **URL:** `http://localhost:8000/api/docs/`
- Muestra todos los endpoints con su documentación

---

## 🔒 Usar Token en Otras Requests

Una vez tengas el `access` token, úsalo en el header de cualquier otra request:

```bash
curl -X GET http://localhost:8000/api/productos/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

---

## 🐛 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'django'`
→ Falta activar venv: `venv\Scripts\activate`

### Error: `No module named 'usuarios'` en imports
→ Falta correr `python manage.py migrate`

### Error: `DATABASES Error: Could not connect to database`
→ PostgreSQL no está corriendo. Verifica `.env` y que `DB_HOST` apunta a la DB correcta.

### Error: `Invalid token` o `Token is blacklisted`
→ El token expiró o fue invalidado. Obtén uno nuevo con `/api/token/`

---

## 📋 Próximos Pasos

1. **Implementar endpoints de productos** — CRUD completo
2. **Agregar permisos por rol** — Admin vs Cajero
3. **Implementar logout/blacklist** — si lo necesitas
4. **Tests** — cuando requieras cobertura
