import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Category(models.Model):
    name  = models.CharField(max_length=100, verbose_name='Nombre')
    slug  = models.SlugField(max_length=200, unique=True, blank=True)
    icon  = models.CharField(max_length=10, default='📚', verbose_name='Emoji')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name        = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering            = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner',     'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced',     'Avanzado'),
    ]

    title       = models.CharField(max_length=200, verbose_name='Título')
    slug        = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(verbose_name='Descripción')
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True,
                                    related_name='courses', verbose_name='Categoría')
    instructor  = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='courses_taught', verbose_name='Instructor')
    emoji       = models.CharField(max_length=10, default='📚', verbose_name='Emoji')
    featured_image = models.ImageField(
        upload_to='courses/images/', null=True, blank=True, verbose_name='Imagen destacada'
    )
    price       = models.DecimalField(max_digits=8, decimal_places=2, default=0.00,
                                      verbose_name='Precio (USD)')
    level       = models.CharField(max_length=20, choices=LEVEL_CHOICES,
                                   default='beginner', verbose_name='Nivel')
    training_plan = models.ForeignKey(
        'TrainingPlan', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='courses', verbose_name='Plan de capacitación'
    )
    categories  = models.ManyToManyField(
        'Category', blank=True,
        related_name='tagged_courses', verbose_name='Categorías'
    )
    is_featured  = models.BooleanField(default=False, verbose_name='Curso destacado')
    is_published = models.BooleanField(default=False, verbose_name='Publicado')
    # Acceso demo
    demo_url      = models.URLField(blank=True, verbose_name='URL de acceso demo')
    demo_login    = models.CharField(max_length=255, blank=True, verbose_name='Usuario demo')
    demo_password = models.CharField(max_length=255, blank=True, verbose_name='Contraseña demo')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering            = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0


class Enrollment(models.Model):
    student    = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='enrollments', verbose_name='Estudiante')
    course     = models.ForeignKey(Course, on_delete=models.CASCADE,
                                   related_name='enrollments', verbose_name='Curso')
    progress   = models.PositiveSmallIntegerField(default=0, verbose_name='Progreso (%)')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha inscripción')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha completado')

    class Meta:
        verbose_name        = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        unique_together     = ('student', 'course')
        ordering            = ['-enrolled_at']

    def __str__(self):
        return f'{self.student.username} → {self.course.title}'


class TrainingPlan(models.Model):
    name           = models.CharField(max_length=200, verbose_name='Nombre')
    description    = models.TextField(blank=True, verbose_name='Descripción')
    is_active      = models.BooleanField(default=True, verbose_name='Activo')
    register_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                                      verbose_name='Token de registro')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Plan de capacitación'
        verbose_name_plural = 'Planes de capacitación'
        ordering            = ['name']

    def __str__(self):
        return self.name


class Topic(models.Model):
    name        = models.CharField(max_length=200, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    course      = models.ForeignKey(
        'Course', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='topics', verbose_name='Curso'
    )
    is_active   = models.BooleanField(default=True, verbose_name='Activo')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    title    = models.CharField(max_length=200, verbose_name='Título')
    course   = models.ForeignKey(
        'Course', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lessons', verbose_name='Curso'
    )
    topic    = models.ForeignKey(
        'Topic', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lessons', verbose_name='Temario'
    )
    content  = models.TextField(blank=True, verbose_name='Texto')
    video    = models.FileField(
        upload_to='lessons/videos/', null=True, blank=True, verbose_name='Video'
    )
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    order    = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Clase'
        verbose_name_plural = 'Clases'
        ordering            = ['course', 'topic', 'order', 'title']

    def __str__(self):
        return self.title


class LessonAttachment(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE,
        related_name='attachments', verbose_name='Clase'
    )
    file   = models.FileField(upload_to='lessons/attachments/', verbose_name='Archivo')
    name   = models.CharField(max_length=255, verbose_name='Nombre')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Adjunto'
        verbose_name_plural = 'Adjuntos'
        ordering            = ['name']

    def __str__(self):
        return self.name


class LessonProgress(models.Model):
    student      = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='lesson_progress', verbose_name='Estudiante')
    lesson       = models.ForeignKey(Lesson, on_delete=models.CASCADE,
                                     related_name='progress_records', verbose_name='Clase')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Completado el')

    class Meta:
        verbose_name        = 'Progreso de clase'
        verbose_name_plural = 'Progreso de clases'
        unique_together     = ('student', 'lesson')

    def __str__(self):
        return f'{self.student.username} ✓ {self.lesson.title}'


# ─── EXÁMENES ────────────────────────────────────────────────────

class Exam(models.Model):
    course        = models.OneToOneField(
        Course, on_delete=models.CASCADE,
        related_name='exam', verbose_name='Curso'
    )
    title         = models.CharField(max_length=200, verbose_name='Título')
    description   = models.TextField(blank=True, verbose_name='Descripción')
    passing_score = models.PositiveSmallIntegerField(
        default=80, verbose_name='Nota mínima para aprobar (%)'
    )
    is_active     = models.BooleanField(default=True, verbose_name='Activo')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Examen'
        verbose_name_plural = 'Exámenes'

    def __str__(self):
        return self.title


class Question(models.Model):
    TYPE_CHOICES = [
        ('multiple', 'Opción múltiple'),
        ('upload',   'Subir archivo'),
    ]
    exam  = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        related_name='questions', verbose_name='Examen'
    )
    text          = models.TextField(verbose_name='Pregunta')
    question_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='multiple',
        verbose_name='Tipo de pregunta'
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name        = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        ordering            = ['exam', 'order']

    def __str__(self):
        return f'P{self.order}: {self.text[:60]}'


class Choice(models.Model):
    question   = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='choices', verbose_name='Pregunta'
    )
    text       = models.CharField(max_length=300, verbose_name='Opción')
    is_correct = models.BooleanField(default=False, verbose_name='Correcta')
    order      = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name        = 'Opción'
        verbose_name_plural = 'Opciones'
        ordering            = ['question', 'order']

    def __str__(self):
        return self.text


class ExamAttempt(models.Model):
    student      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='exam_attempts', verbose_name='Estudiante'
    )
    exam         = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        related_name='attempts', verbose_name='Examen'
    )
    score        = models.PositiveSmallIntegerField(default=0, verbose_name='Puntuación (%)')
    passed       = models.BooleanField(default=False, verbose_name='Aprobado')
    attempted_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        verbose_name        = 'Intento de examen'
        verbose_name_plural = 'Intentos de examen'
        ordering            = ['-attempted_at']

    def __str__(self):
        return f'{self.student.username} – {self.exam.title} – {self.score}%'


class ExamUpload(models.Model):
    attempt  = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE,
        related_name='uploads', verbose_name='Intento'
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='uploads', verbose_name='Pregunta'
    )
    file     = models.FileField(upload_to='exam_uploads/', verbose_name='Archivo')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f'{self.attempt} – {self.question.text[:40]}'


# ─── COMENTARIOS DE CLASE ────────────────────────────────────────

class LessonComment(models.Model):
    lesson     = models.ForeignKey(
        Lesson, on_delete=models.CASCADE,
        related_name='comments', verbose_name='Clase'
    )
    author     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='lesson_comments', verbose_name='Autor'
    )
    parent     = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies', verbose_name='Respuesta a'
    )
    content    = models.TextField(verbose_name='Comentario')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering            = ['created_at']

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}'


# ─── VALORACIONES DE CURSO ───────────────────────────────────────

class CourseReview(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    course     = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='reviews', verbose_name='Curso'
    )
    student    = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='course_reviews', verbose_name='Estudiante'
    )
    rating     = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, verbose_name='Valoración'
    )
    comment    = models.TextField(blank=True, verbose_name='Comentario')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Valoración'
        verbose_name_plural = 'Valoraciones'
        unique_together     = ('course', 'student')
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.student.username} → {self.course.title}: {self.rating}★'


# ─── TAREAS ──────────────────────────────────────────────────────

class Task(models.Model):
    lesson               = models.ForeignKey(
        Lesson, on_delete=models.CASCADE,
        related_name='tasks', verbose_name='Clase'
    )
    title                = models.CharField(max_length=200, verbose_name='Nombre')
    description          = models.TextField(blank=True, verbose_name='Descripción')
    requires_attachment  = models.BooleanField(default=False, verbose_name='Solicitar adjunto')
    order                = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    is_active            = models.BooleanField(default=True, verbose_name='Activa')
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering            = ['lesson', 'order']

    def __str__(self):
        return self.title


class TaskSubmission(models.Model):
    task        = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name='submissions', verbose_name='Tarea'
    )
    student     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='task_submissions', verbose_name='Estudiante'
    )
    attachment  = models.FileField(
        upload_to='task_submissions/', null=True, blank=True,
        verbose_name='Adjunto'
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Entrega de tarea'
        verbose_name_plural = 'Entregas de tareas'
        unique_together     = ('task', 'student')

    def __str__(self):
        return f'{self.student.username} → {self.task.title}'


# ─── BIBLIOTECA DE DOCUMENTOS ────────────────────────────────────

class DocFolder(models.Model):
    name       = models.CharField(max_length=200, verbose_name='Nombre')
    parent     = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subfolders', verbose_name='Carpeta padre'
    )
    order      = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Carpeta'
        verbose_name_plural = 'Carpetas'
        ordering            = ['order', 'name']

    def __str__(self):
        return self.name

    def breadcrumb(self):
        """Returns list of ancestors from root to self."""
        crumbs, node = [], self
        while node:
            crumbs.insert(0, node)
            node = node.parent
        return crumbs


class DocFile(models.Model):
    folder     = models.ForeignKey(
        DocFolder, on_delete=models.CASCADE,
        related_name='files', verbose_name='Carpeta'
    )
    name       = models.CharField(max_length=255, verbose_name='Nombre')
    file       = models.FileField(upload_to='biblioteca/', verbose_name='Archivo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @property
    def extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')


# ─── BLOG / ARTÍCULOS ────────────────────────────────────────────

class Article(models.Model):
    title       = models.CharField(max_length=255, verbose_name='Título')
    slug        = models.SlugField(max_length=200, unique=True, blank=True)
    summary     = models.TextField(blank=True, verbose_name='Resumen')
    content     = models.TextField(verbose_name='Contenido')
    cover_image = models.ImageField(
        upload_to='articles/', null=True, blank=True, verbose_name='Imagen de portada'
    )
    author      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='articles', verbose_name='Autor'
    )
    is_published = models.BooleanField(default=False, verbose_name='Publicado')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Artículo'
        verbose_name_plural = 'Artículos'
        ordering            = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ArticleComment(models.Model):
    article    = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='comments', verbose_name='Artículo'
    )
    author     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='article_comments', verbose_name='Autor'
    )
    content    = models.TextField(verbose_name='Comentario')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Comentario de artículo'
        verbose_name_plural = 'Comentarios de artículos'
        ordering            = ['created_at']

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}'

# ─── PROFESORES: VALORACIONES Y MENSAJES ─────────────────

class TeacherRating(models.Model):
    teacher    = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='teacher_ratings', verbose_name='Profesor')
    student    = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='given_teacher_ratings', verbose_name='Estudiante')
    rating     = models.PositiveSmallIntegerField(
        default=5, verbose_name='Valoración',
        choices=[(1,'1 estrella'),(2,'2 estrellas'),(3,'3 estrellas'),(4,'4 estrellas'),(5,'5 estrellas')]
    )
    comment    = models.TextField(blank=True, verbose_name='Comentario público')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Valoración de profesor'
        verbose_name_plural = 'Valoraciones de profesores'
        unique_together     = ('teacher', 'student')
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.student.username} -> {self.teacher.username}: {self.rating}*'


class TeacherMessage(models.Model):
    teacher    = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='teacher_inbox', verbose_name='Profesor')
    student    = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='student_outbox', verbose_name='Estudiante')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='sent_teacher_msgs', verbose_name='Remitente')
    content    = models.TextField(verbose_name='Mensaje')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Mensaje a profesor'
        verbose_name_plural = 'Mensajes a profesores'
        ordering            = ['created_at']

    def __str__(self):
        return f'{self.sender.username}: {self.content[:40]}'


# ─── MIS DOCUMENTOS ──────────────────────────────────────────────

class UserFolder(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_folders')
    name       = models.CharField(max_length=200, verbose_name='Nombre')
    parent     = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_token     = models.UUIDField(null=True, blank=True, unique=True, verbose_name='Token de compartir')
    view_count      = models.PositiveIntegerField(default=0, verbose_name='Aperturas')
    shared_with_all = models.BooleanField(default=False, verbose_name='Compartida con todos')
    capture_token   = models.UUIDField(null=True, blank=True, unique=True, verbose_name='Token de captura')

    class Meta:
        verbose_name        = 'Carpeta personal'
        verbose_name_plural = 'Carpetas personales'
        ordering            = ['name']
        unique_together     = ('user', 'parent', 'name')

    def __str__(self):
        return self.name

    @property
    def is_shared(self):
        return self.share_token is not None

    def breadcrumb(self):
        crumbs = []
        node = self
        while node:
            crumbs.insert(0, node)
            node = node.parent
        return crumbs


class UserFile(models.Model):
    folder     = models.ForeignKey(UserFolder, on_delete=models.CASCADE, related_name='files')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_files')
    name       = models.CharField(max_length=255, verbose_name='Nombre')
    file       = models.FileField(upload_to='user_docs/', verbose_name='Archivo')
    created_at = models.DateTimeField(auto_now_add=True)
    share_token = models.UUIDField(null=True, blank=True, unique=True, verbose_name='Token de compartir')
    view_count  = models.PositiveIntegerField(default=0, verbose_name='Aperturas')

    class Meta:
        verbose_name        = 'Archivo personal'
        verbose_name_plural = 'Archivos personales'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @property
    def is_shared(self):
        return self.share_token is not None

    @property
    def extension(self):
        import os
        return os.path.splitext(self.name)[1].lower().lstrip('.')


class UserNote(models.Model):
    folder       = models.ForeignKey(UserFolder, on_delete=models.CASCADE, related_name='notes')
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_notes')
    title        = models.CharField(max_length=255, verbose_name='Título')
    content      = models.TextField(blank=True, verbose_name='Contenido')
    share_token  = models.UUIDField(null=True, blank=True, unique=True, verbose_name='Token de compartir')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Nota personal'
        verbose_name_plural = 'Notas personales'
        ordering            = ['-updated_at']

    def __str__(self):
        return self.title

    @property
    def is_shared(self):
        return self.share_token is not None


# ─── PIZARRAS (WHITEBOARD) ────────────────────────────────────────

class UserWhiteboard(models.Model):
    folder      = models.ForeignKey(
        UserFolder, on_delete=models.CASCADE, null=True, blank=True,
        related_name='whiteboards', verbose_name='Carpeta'
    )
    user        = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='my_whiteboards', verbose_name='Usuario'
    )
    title       = models.CharField(max_length=255, default='Pizarra sin título', verbose_name='Título')
    data        = models.TextField(blank=True, default='', verbose_name='Datos JSON')
    share_token = models.UUIDField(null=True, blank=True, unique=True, verbose_name='Token público')
    view_count  = models.PositiveIntegerField(default=0, verbose_name='Aperturas')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Pizarra'
        verbose_name_plural = 'Pizarras'
        ordering            = ['-updated_at']

    def __str__(self):
        return self.title

    @property
    def is_shared(self):
        return self.share_token is not None


# ─── PLANOS CAD ───────────────────────────────────────────────────────────────

class UserCAD(models.Model):
    folder      = models.ForeignKey(
        UserFolder, on_delete=models.CASCADE, null=True, blank=True,
        related_name='cad_files', verbose_name='Carpeta'
    )
    user        = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='my_cad_files', verbose_name='Usuario'
    )
    title       = models.CharField(max_length=255, default='Plano sin título', verbose_name='Título')
    data        = models.TextField(blank=True, default='', verbose_name='Datos JSON (Fabric.js)')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Plano CAD'
        verbose_name_plural = 'Planos CAD'
        ordering            = ['-updated_at']

    def __str__(self):
        return self.title


class FolderShare(models.Model):
    folder       = models.ForeignKey('UserFolder', on_delete=models.CASCADE,
                                     related_name='direct_shares', verbose_name='Carpeta')
    shared_by    = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='folders_shared_out', verbose_name='Compartido por')
    with_user    = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='folders_shared_in', verbose_name='Con usuario')
    with_company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='shared_folders', verbose_name='Con empresa')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Carpeta compartida'
        verbose_name_plural = 'Carpetas compartidas'
        ordering            = ['-created_at']

    def __str__(self):
        target = f'@{self.with_user.username}' if self.with_user_id else str(self.with_company)
        return f'"{self.folder.name}" → {target}'


# ─── PLANTILLA DEMO ─────────────────────────────────────────────────────────────

PRESENTATION_DEMO = """\
# Mi Presentación
### Subtítulo aquí

> Creada con **Nooxial**

---

## Agenda

1. Introducción
2. Desarrollo
3. Conclusión

---

## Puntos clave

- Punto **uno** — lo más importante
- Punto *dos* — complementario
- Punto `tres` — detalle técnico

--

### Profundizando

> Los subslides se crean con `--`  
> Los slides horizontales con `---`

---

## Código

```python
def hola_mundo():
    print("¡Hola desde Nooxial! 🎉")
    return True
```

---

## Imagen

![Logo](https://via.placeholder.com/400x200?text=Tu+imagen+aquí)

---

## Cita

> El conocimiento es poder.
>
> — Francis Bacon

---

## ¡Gracias!

### ¿Preguntas?

📧 &nbsp;contacto@tudominio.com
"""


# ─── PRESENTACIONES ─────────────────────────────────────────────────────────────

REVEAL_THEMES = [
    ('black',     'Negro'),
    ('white',     'Blanco'),
    ('league',    'League'),
    ('beige',     'Beige'),
    ('sky',       'Cielo'),
    ('night',     'Noche'),
    ('serif',     'Serif'),
    ('simple',    'Simple'),
    ('solarized', 'Solarized'),
    ('moon',      'Luna'),
    ('dracula',   'Dracula'),
]


class UserPresentation(models.Model):
    folder     = models.ForeignKey(
        UserFolder, on_delete=models.CASCADE, null=True, blank=True,
        related_name='presentations', verbose_name='Carpeta',
    )
    user       = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='my_presentations', verbose_name='Usuario',
    )
    title      = models.CharField(max_length=255, default='Presentación sin título',
                                  verbose_name='Título')
    content    = models.TextField(blank=True, verbose_name='Contenido Markdown')
    theme      = models.CharField(max_length=30, default='black',
                                  choices=REVEAL_THEMES, verbose_name='Tema')
    share_token = models.UUIDField(null=True, blank=True, unique=True, verbose_name='Token público')
    view_count  = models.PositiveIntegerField(default=0, verbose_name='Vistas públicas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Presentación'
        verbose_name_plural = 'Presentaciones'
        ordering            = ['-updated_at']

    def __str__(self):
        return self.title


# ─── ENLACES GUARDADOS ───────────────────────────────────────────────────────

class SavedLink(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_links')
    name       = models.CharField(max_length=200, verbose_name='Nombre')
    url        = models.URLField(max_length=2000, verbose_name='URL')
    link_user  = models.CharField(max_length=200, blank=True, verbose_name='Usuario')
    link_pass  = models.CharField(max_length=500, blank=True, verbose_name='Contraseña')
    is_public  = models.BooleanField(default=True, verbose_name='Pública')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Enlace guardado'
        verbose_name_plural = 'Enlaces guardados'
        ordering            = ['-created_at']

    def __str__(self):
        return self.name


# ─── LISTAS DE CHEQUEO ───────────────────────────────────────────────────────

class Checklist(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checklists')
    name        = models.CharField(max_length=200, verbose_name='Nombre')
    is_public   = models.BooleanField(default=True, verbose_name='Pública')
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Lista de chequeo'
        verbose_name_plural = 'Listas de chequeo'
        ordering            = ['-updated_at']

    def __str__(self):
        return self.name

    @property
    def done_count(self):
        return self.items.filter(is_done=True).count()

    @property
    def total_count(self):
        return self.items.count()


class ChecklistItem(models.Model):
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='items')
    text      = models.CharField(max_length=500, verbose_name='Tarea')
    is_done   = models.BooleanField(default=False)
    order     = models.PositiveSmallIntegerField(default=0)
    duration  = models.PositiveSmallIntegerField(default=1, verbose_name='Duración (unidades)')

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return self.text