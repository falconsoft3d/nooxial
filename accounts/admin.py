from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html


class EnrollmentInline(admin.TabularInline):
    from courses.models import Enrollment
    model  = Enrollment
    extra  = 0
    fields = ('course', 'progress', 'enrolled_at')
    readonly_fields = ('enrolled_at',)
    verbose_name = 'Curso inscrito'
    verbose_name_plural = 'Cursos inscritos'


class NooxialUserAdmin(BaseUserAdmin):
    list_display  = ('username', 'full_name', 'email', 'date_joined',
                     'is_active', 'enrollment_count', 'is_staff')
    list_filter   = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    inlines       = [EnrollmentInline]

    @admin.display(description='Nombre completo')
    def full_name(self, obj):
        name = obj.get_full_name()
        return name if name else '—'

    @admin.display(description='Cursos')
    def enrollment_count(self, obj):
        count = obj.enrollments.count()
        return format_html(
            '<span style="background:#9fe870;color:#111;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700">{}</span>',
            count
        )


admin.site.unregister(User)
admin.site.register(User, NooxialUserAdmin)

# ─── Admin site branding ────────────────────────────────────────
admin.site.site_header  = '🟢 Nooxial Admin'
admin.site.site_title   = 'Nooxial'
admin.site.index_title  = 'Panel de administración'

