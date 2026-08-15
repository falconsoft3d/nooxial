# Nooxial — Plataforma LMS

**Nooxial** es un sistema de gestión del aprendizaje (LMS) completo construido con Django 6.1. Permite crear y gestionar cursos, clases, tareas y exámenes con certificados digitales, blog y biblioteca de documentos.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Django 6.1 · Python 3.14 |
| Base de datos | SQLite (desarrollo) / PostgreSQL (producción) |
| CSS | Tailwind CSS (CDN) |
| Imágenes / archivos | Pillow · FileField |
| QR en certificados | qrcode |
| Servidor producción | Gunicorn + Nginx |

---

## Características principales

### 👥 Gestión de usuarios
- Registro, login y perfil con foto de perfil y firma digital
- Login con email **o** nombre de usuario
- Panel de administración estilo Odoo con todos los menús

### 📚 Cursos y contenido
- Cursos con imagen destacada, categorías, precio y nivel
- Temas → Clases con vídeo, texto y adjuntos múltiples
- Marcado de clases como completadas (auto-marcado al terminar vídeo)
- Progreso calculado en tiempo real

### 📋 Tareas
- Tareas por clase con descripción y solicitud de adjunto opcional
- Panel de entregas visible para el administrador
- Las tareas pendientes se destacan en naranja en el detalle del curso

### 🎓 Exámenes y certificados
- Exámenes con preguntas de opción múltiple y preguntas de adjunto
- Nota mínima configurable por examen (por defecto 80%)
- Intentos ilimitados
- Certificado PDF imprimible con firma del instructor, firma del estudiante y **código QR de verificación**
- Página pública de validación del certificado (`/verificar/<id>/`)

### ⭐ Valoraciones
- Los estudiantes inscritos pueden puntuar cursos con 1-5 estrellas y comentarios
- Las estrellas aparecen en las tarjetas de cursos (home, catálogo, dashboard)

### 💬 Soporte
- Widget flotante de chat en toda la web (usuarios logueados)
- Bandeja de entrada de tickets para el administrador con respuestas por hilo

### 📄 Blog
- Artículos con imagen de portada, resumen y contenido
- Comentarios públicos para usuarios logueados
- Relacionados al pie de cada artículo

### 📁 Biblioteca de documentos
- Carpetas y subcarpetas ilimitadas
- Subida de archivos múltiples por carpeta
- Vista de solo lectura para estudiantes en el dashboard

### ⚙️ Configuración general
- Activar/desactivar registro de nuevos usuarios
- Modo mantenimiento
- Nombre del sitio

---

## Instalación local

```bash
# 1. Clonar
git clone https://github.com/TU_USUARIO/nooxial.git
cd nooxial

# 2. Entorno virtual
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Migraciones
python manage.py migrate

# 5. Superusuario
python manage.py createsuperuser

# 6. Ejecutar
python manage.py runserver
```

Accede a `http://localhost:8000` y al panel de administración desde el dashboard tras iniciar sesión con el superusuario.

---

## Estructura del proyecto

```
nooxial/
├── accounts/          # Auth, perfiles, panel de administración
│   ├── models.py      # UserProfile, SiteConfig, SupportTicket/Message
│   ├── views.py       # Vistas admin + auth
│   └── urls.py
├── courses/           # Toda la lógica de cursos
│   ├── models.py      # Course, Lesson, Topic, Task, Exam, Article, DocFolder…
│   ├── views.py       # Vistas de estudiante (dashboard, cursos, exámenes…)
│   └── urls.py
├── core/              # Home, blog público
│   ├── views.py
│   └── urls.py
├── config/            # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── templates/         # Todos los templates HTML
│   ├── base.html
│   ├── dashboard_base.html
│   ├── accounts/
│   ├── courses/
│   └── core/
├── static/            # CSS, JS, imágenes estáticas
├── media/             # Archivos subidos por usuarios (ignorado en git)
├── requirements.txt
├── .gitignore
└── deploy.md          # Guía de despliegue en producción
```

---

## Variables de entorno recomendadas para producción

Crea un archivo `.env` (no incluido en git):

```env
SECRET_KEY=genera_una_clave_segura
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
DATABASE_URL=postgres://u_nooxial:PASSWORD@localhost/nooxial_prod
```

---

## Despliegue en producción

Ver [deploy.md](deploy.md) para instrucciones completas con Nginx + Gunicorn + PostgreSQL + SSL.

---

## Licencia

Proyecto privado. Todos los derechos reservados.
