# Instrucciones del Proyecto - Sistema POS

## Stack tecnológico
- Python 3.10+
- Django 4+
- Django REST Framework
- PostgreSQL

## Convención de ramas
- `main`: producción (protegida)
- `develop`: integración (protegida)
- `feature/*`: desarrollo por tarea

## Convención de commits
Se debe usar **Conventional Commits**:
- `feat:` nueva funcionalidad
- `fix:` corrección de errores
- `docs:` cambios de documentación
- `refactor:` mejoras internas sin cambio funcional
- `test:` creación o ajuste de pruebas

## Reglas obligatorias
1. No se permite push directo a `main` ni `develop`.
2. Todo cambio debe ingresar mediante **Pull Request**.
3. Cada Pull Request debe estar ligado a un Issue.
4. Todo PR debe pasar revisión antes de merge.
5. El merge a `main` solo se realiza desde cambios validados en `develop`.

## Buenas prácticas del equipo
- Crear ramas pequeñas y enfocadas a una sola tarea.
- Hacer commits atómicos y con mensajes claros.
- Mantener los PRs pequeños para acelerar revisión.
- Actualizar documentación cuando cambie comportamiento funcional.
- Resolver comentarios de revisión antes de solicitar merge.
- Validar migraciones y compatibilidad con PostgreSQL antes de aprobar.
- Evitar deuda técnica: dejar TODOs con contexto y issue asociado.
