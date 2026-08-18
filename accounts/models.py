import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ─── EMPRESAS ────────────────────────────────────────────────

class Company(models.Model):
    name       = models.CharField(max_length=200, verbose_name='Nombre')
    email      = models.EmailField(blank=True, verbose_name='Correo electrónico')
    phone      = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    web        = models.URLField(blank=True, verbose_name='Sitio web')
    address    = models.CharField(max_length=255, blank=True, verbose_name='Dirección')
    nif        = models.CharField(max_length=50, blank=True, verbose_name='NIF / CIF')
    public_token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                                         verbose_name='Token público')
    attendance_token   = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                                          verbose_name='Token de asistencia')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @property
    def user_count(self):
        return self.users.count()


class UserProfile(models.Model):
    user      = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo     = models.ImageField(
        upload_to='profile_photos/', null=True, blank=True, verbose_name='Foto de perfil'
    )
    signature = models.TextField(blank=True, verbose_name='Firma (base64)',
                                 help_text='Datos de la firma dibujada en canvas')
    company   = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', verbose_name='Empresa'
    )
    pin_hash  = models.CharField(
        max_length=128, blank=True, verbose_name='PIN de bloqueo (hash)'
    )
    cv_headline    = models.CharField(max_length=200, blank=True, verbose_name='Titular profesional')
    cv_phone       = models.CharField(max_length=30, blank=True, verbose_name='Teléfono de contacto')
    cv_linkedin    = models.URLField(blank=True, verbose_name='LinkedIn')
    cv_instagram   = models.URLField(blank=True, verbose_name='Instagram')
    cv_facebook    = models.URLField(blank=True, verbose_name='Facebook')
    cv_tiktok      = models.URLField(blank=True, verbose_name='TikTok')
    cv_github      = models.URLField(blank=True, verbose_name='GitHub')
    cv_summary     = models.TextField(blank=True, verbose_name='Resumen profesional')
    cv_experience  = models.TextField(blank=True, verbose_name='Experiencia laboral')
    cv_education   = models.TextField(blank=True, verbose_name='Formación académica')
    cv_skills      = models.TextField(blank=True, verbose_name='Habilidades y competencias')
    cv_public          = models.BooleanField(default=False, verbose_name='Currículum público')
    nav_more_expanded  = models.BooleanField(default=False, verbose_name='Menú expandido')

    class Meta:
        verbose_name        = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def __str__(self):
        return f'Perfil de {self.user.username}'

    @property
    def has_pin(self):
        return bool(self.pin_hash and self.pin_hash.strip())

    @property
    def has_signature(self):
        return bool(self.signature and self.signature.strip())


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


# ─── CONFIGURACIÓN DEL SITIO ─────────────────────────────────────

class SiteConfig(models.Model):
    """Singleton — solo debe existir una fila."""
    enable_registration = models.BooleanField(
        default=True,
        verbose_name='Permitir registro de nuevos usuarios'
    )
    site_name           = models.CharField(
        max_length=100, default='Nooxial', verbose_name='Nombre del sitio'
    )
    maintenance_mode    = models.BooleanField(
        default=False, verbose_name='Modo mantenimiento'
    )

    # ── Configuración de email ──────────────────────────────────
    email_host          = models.CharField(
        max_length=255, default='smtp.gmail.com', blank=True, verbose_name='Servidor SMTP'
    )
    email_port          = models.PositiveIntegerField(
        default=587, verbose_name='Puerto SMTP'
    )
    email_host_user     = models.CharField(
        max_length=255, blank=True, verbose_name='Usuario SMTP (email remitente)'
    )
    email_host_password = models.CharField(
        max_length=255, blank=True, verbose_name='Contraseña SMTP'
    )
    email_use_tls       = models.BooleanField(
        default=True, verbose_name='Usar TLS'
    )
    email_use_ssl       = models.BooleanField(
        default=False, verbose_name='Usar SSL'
    )
    default_from_email  = models.CharField(
        max_length=255, blank=True, verbose_name='Dirección "De" por defecto',
        help_text='Ej: Nooxial <no-reply@tudominio.com>. Si está vacío se usa el usuario SMTP.'
    )
    send_welcome_email  = models.BooleanField(
        default=False, verbose_name='Enviar email de bienvenida al registrarse'
    )
    cookie_consent_enabled = models.BooleanField(
        default=True, verbose_name='Mostrar aviso de cookies'
    )
    cookie_consent_text = models.TextField(
        blank=True,
        verbose_name='Texto del aviso de cookies',
        default=(
            'Utilizamos cookies propias y de terceros para mejorar tu experiencia, '
            'analizar el tráfico y personalizar el contenido de acuerdo con nuestra '
            'Política de Privacidad. Al hacer clic en "Aceptar" consientes el uso '
            'de todas las cookies. Puedes gestionar tus preferencias en cualquier momento.'
        )
    )

    class Meta:
        verbose_name        = 'Configuración general'
        verbose_name_plural = 'Configuración general'

    def __str__(self):
        return 'Configuración general'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ─── SOPORTE ────────────────────────────────────────────────────

class SupportTicket(models.Model):
    STATUS_CHOICES = [('open', 'Abierto'), ('closed', 'Cerrado')]
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='support_tickets', verbose_name='Usuario')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Ticket #{self.pk} – {self.user.username}'

    @property
    def unread_by_staff(self):
        return self.messages.filter(is_staff_reply=False, is_read=False).exists()

    @property
    def unread_by_user(self):
        return self.messages.filter(is_staff_reply=True, is_read=False).exists()


class SupportMessage(models.Model):
    ticket         = models.ForeignKey(SupportTicket, on_delete=models.CASCADE,
                                       related_name='messages', verbose_name='Ticket')
    author         = models.ForeignKey(User, on_delete=models.CASCADE,
                                       related_name='support_messages', verbose_name='Autor')
    content        = models.TextField(verbose_name='Mensaje')
    is_staff_reply = models.BooleanField(default=False, verbose_name='Respuesta de staff')
    is_read        = models.BooleanField(default=False, verbose_name='Leído')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Msg #{self.pk} – Ticket #{self.ticket_id}'


# ─── RECUPERACIÓN DE CONTRASEÑA ──────────────────────────────────

class PasswordResetToken(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='password_reset_tokens')
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used       = models.BooleanField(default=False)

    class Meta:
        verbose_name        = 'Token de recuperación'
        verbose_name_plural = 'Tokens de recuperación'

    def __str__(self):
        return f'Reset token para {self.user.username}'

    def is_valid(self):
        from django.utils import timezone
        from datetime import timedelta
        return not self.used and (timezone.now() - self.created_at) < timedelta(hours=2)


# ─── VOTACIONES ──────────────────────────────────────────────────

class Voting(models.Model):
    name         = models.CharField(max_length=200, verbose_name='Nombre de la votación')
    description  = models.TextField(blank=True, verbose_name='Descripción')
    is_active    = models.BooleanField(default=True, verbose_name='Activa')
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    ends_at      = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de cierre')

    class Meta:
        verbose_name        = 'Votación'
        verbose_name_plural = 'Votaciones'
        ordering            = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def total_votes(self):
        return self.votes.count()

    @property
    def is_open(self):
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.ends_at and timezone.now() > self.ends_at:
            return False
        return True


class VotingOption(models.Model):
    voting  = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='options')
    name    = models.CharField(max_length=200, verbose_name='Opción')
    order   = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.voting.name} → {self.name}'

    @property
    def vote_count(self):
        return self.votes.count()

    def vote_percent(self, total):
        if not total:
            return 0
        return round(self.votes.count() / total * 100)


class Vote(models.Model):
    voting       = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='votes')
    option       = models.ForeignKey(VotingOption, on_delete=models.CASCADE, related_name='votes')
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='votes')
    voter_name   = models.CharField(max_length=200, blank=True, verbose_name='Nombre')
    voter_email  = models.EmailField(blank=True, verbose_name='Email')
    voter_phone  = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Voto'
        verbose_name_plural = 'Votos'
        ordering            = ['-created_at']

    def __str__(self):
        who = self.user.username if self.user else self.voter_name
        return f'{who} → {self.option.name}'


# ─── ASISTENCIAS DE EMPRESA ──────────────────────────────────────

class Attendance(models.Model):
    company    = models.ForeignKey(Company, on_delete=models.CASCADE,
                                   related_name='attendances', verbose_name='Empresa')
    name       = models.CharField(max_length=200, verbose_name='Nombre')
    email      = models.EmailField(blank=True, verbose_name='Email')
    phone      = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    position   = models.CharField(max_length=100, blank=True, verbose_name='Cargo')
    notes      = models.TextField(blank=True, verbose_name='Notas')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.name} – {self.company.name}'


# ─── CONTACTOS ───────────────────────────────────────────────────

class Contact(models.Model):
    first_name = models.CharField(max_length=100, verbose_name='Nombre')
    last_name  = models.CharField(max_length=100, blank=True, verbose_name='Apellidos')
    email      = models.EmailField(verbose_name='Email')
    phone      = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    company    = models.CharField(max_length=200, blank=True, verbose_name='Empresa')
    position   = models.CharField(max_length=100, blank=True, verbose_name='Cargo')
    message    = models.TextField(blank=True, verbose_name='Mensaje')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Contacto'
        verbose_name_plural = 'Contactos'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} <{self.email}>'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()



# ─── MENSAJES DIRECTOS ───────────────────────────────────────────

class DirectMessage(models.Model):
    sender     = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='dm_sent', verbose_name='Remitente')
    recipient  = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='dm_received', verbose_name='Destinatario')
    content    = models.TextField(verbose_name='Mensaje')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Mensaje directo'
        verbose_name_plural = 'Mensajes directos'
        ordering            = ['created_at']

    def __str__(self):
        return f'{self.sender.username} → {self.recipient.username}: {self.content[:40]}'


# ─── TÉRMINOS Y CONDICIONES ──────────────────────────────────────

class TermsConditions(models.Model):
    title       = models.CharField(max_length=200, default='Términos y Condiciones', verbose_name='Título')
    description = models.TextField(verbose_name='Contenido')
    version     = models.CharField(max_length=20, blank=True, verbose_name='Versión')
    is_active   = models.BooleanField(default=False, verbose_name='Activo (requiere aceptación)')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Términos y condiciones'
        verbose_name_plural = 'Términos y condiciones'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.title} v{self.version}' if self.version else self.title

    def save(self, *args, **kwargs):
        # Solo puede haber un T&C activo a la vez
        if self.is_active:
            TermsConditions.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


class TermsAcceptance(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='terms_acceptances')
    terms      = models.ForeignKey(TermsConditions, on_delete=models.CASCADE,
                                   related_name='acceptances')
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Aceptación de términos'
        verbose_name_plural = 'Aceptaciones de términos'
        unique_together     = ('user', 'terms')
        ordering            = ['-accepted_at']

    def __str__(self):
        return f'{self.user.username} aceptó {self.terms}'


# ─── GRUPOS DE CHAT ──────────────────────────────────────────

class ChatGroup(models.Model):
    name        = models.CharField(max_length=200, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    created_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_chat_groups', verbose_name='Creado por'
    )
    companies   = models.ManyToManyField(
        Company, blank=True,
        related_name='chat_groups', verbose_name='Empresas'
    )
    members     = models.ManyToManyField(
        User, blank=True,
        related_name='chat_group_memberships', verbose_name='Miembros individuales'
    )
    is_active   = models.BooleanField(default=True, verbose_name='Activo')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Grupo de chat'
        verbose_name_plural = 'Grupos de chat'
        ordering            = ['name']

    def __str__(self):
        return self.name

    def is_member(self, user):
        """Devuelve True si el usuario pertenece al grupo (directo, empresa o staff)."""
        if user.is_staff:
            return True
        if self.members.filter(pk=user.pk).exists():
            return True
        try:
            company = user.profile.company
            if company and self.companies.filter(pk=company.pk).exists():
                return True
        except Exception:
            pass
        return False

    def get_all_members(self):
        from django.db.models import Q
        direct_ids   = self.members.values_list('pk', flat=True)
        company_ids  = self.companies.values_list('pk', flat=True)
        return User.objects.filter(
            Q(pk__in=direct_ids) | Q(profile__company__pk__in=company_ids)
        ).distinct()


class ChatGroupMessage(models.Model):
    group      = models.ForeignKey(
        ChatGroup, on_delete=models.CASCADE,
        related_name='messages', verbose_name='Grupo'
    )
    sender     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='group_messages_sent', verbose_name='Remitente'
    )
    content    = models.TextField(verbose_name='Mensaje')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Mensaje de grupo'
        verbose_name_plural = 'Mensajes de grupo'
        ordering            = ['created_at']

    def __str__(self):
        return f'[{self.group.name}] {self.sender.username}: {self.content[:40]}'


# ─── SEÑALIZACIÓN WEBRTC (REUNIONES) ─────────────────────────────

class MeetingSignal(models.Model):
    company    = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='meeting_signals'
    )
    peer_id    = models.CharField(max_length=20, verbose_name='Peer origen')
    target     = models.CharField(max_length=20, blank=True, verbose_name='Peer destino')
    stype      = models.CharField(max_length=20, verbose_name='Tipo')  # join|offer|answer|ice|leave|heartbeat
    data       = models.TextField(blank=True, verbose_name='Datos JSON')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Señal WebRTC'
        verbose_name_plural = 'Señales WebRTC'
        ordering            = ['id']

    def __str__(self):
        return f'[{self.company}] {self.peer_id} → {self.target or "all"}: {self.stype}'


# ─── EVALUACIONES DE PLATAFORMA ──────────────────────────────────

class PlatformRating(models.Model):
    RATING_CHOICES = [
        ('happy',   '😊 Feliz'),
        ('neutral', '😐 Neutral'),
        ('sad',     '😞 Triste'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='platform_ratings', verbose_name='Usuario')
    rating     = models.CharField(max_length=10, choices=RATING_CHOICES, verbose_name='Valoración')
    comment    = models.TextField(blank=True, verbose_name='Comentario')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        verbose_name        = 'Evaluación de plataforma'
        verbose_name_plural = 'Evaluaciones de plataforma'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.user.username} – {self.get_rating_display()} – {self.created_at.strftime("%d/%m/%Y")}'


# ─── VERSIONES DE LA PLATAFORMA ──────────────────────────────────────────────────

class AppVersion(models.Model):
    version     = models.CharField(max_length=20, unique=True, verbose_name='Versión')
    title       = models.CharField(max_length=255, verbose_name='Título')
    released_at = models.DateField(verbose_name='Fecha de lanzamiento')
    is_current  = models.BooleanField(default=False, verbose_name='Versión actual')

    class Meta:
        verbose_name        = 'Versión'
        verbose_name_plural = 'Versiones'
        ordering            = ['-released_at']

    def __str__(self):
        return f'v{self.version} — {self.title}'

    def save(self, *args, **kwargs):
        if self.is_current:
            AppVersion.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


FEATURE_CATEGORY = [
    ('feature',     '✨ Novedad'),
    ('improvement', '🔧 Mejora'),
    ('fix',         '🐛 Corrección'),
]


class AppVersionFeature(models.Model):
    version  = models.ForeignKey(AppVersion, on_delete=models.CASCADE,
                                 related_name='features', verbose_name='Versión')
    category = models.CharField(max_length=20, choices=FEATURE_CATEGORY,
                                default='feature', verbose_name='Categoría')
    text     = models.CharField(max_length=500, verbose_name='Descripción')
    order    = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name        = 'Mejora'
        verbose_name_plural = 'Mejoras'
        ordering            = ['order', 'pk']

    def __str__(self):
        return f'{self.get_category_display()} — {self.text[:60]}'
