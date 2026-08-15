from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user      = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo     = models.ImageField(
        upload_to='profile_photos/', null=True, blank=True, verbose_name='Foto de perfil'
    )
    signature = models.TextField(blank=True, verbose_name='Firma (base64)',
                                 help_text='Datos de la firma dibujada en canvas')

    class Meta:
        verbose_name        = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def __str__(self):
        return f'Perfil de {self.user.username}'

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

