from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Course, Enrollment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('icon', 'name', 'slug', 'course_count', 'order')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    @admin.display(description='Cursos')
    def course_count(self, obj):
        return obj.courses.count()


class EnrollmentInline(admin.TabularInline):
    model  = Enrollment
    extra  = 0
    fields = ('student', 'progress', 'enrolled_at', 'completed_at')
    readonly_fields = ('enrolled_at',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display   = ('emoji_title', 'category', 'instructor', 'level',
                      'price_display', 'enrollment_count', 'is_published')
    list_filter    = ('is_published', 'level', 'category')
    search_fields  = ('title', 'description', 'instructor__username')
    list_editable  = ('is_published',)
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('instructor', 'category')
    inlines        = [EnrollmentInline]
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'emoji', 'category', 'instructor'),
        }),
        ('Contenido', {
            'fields': ('description', 'level', 'price', 'is_published'),
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Curso')
    def emoji_title(self, obj):
        return format_html('{} {}', obj.emoji, obj.title)

    @admin.display(description='Precio')
    def price_display(self, obj):
        return 'Gratis' if obj.is_free else f'${obj.price}'

    @admin.display(description='Inscritos')
    def enrollment_count(self, obj):
        return obj.enrollments.count()


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display  = ('student', 'course', 'progress_bar', 'enrolled_at', 'completed_at')
    list_filter   = ('course__category', 'course')
    search_fields = ('student__username', 'student__email', 'course__title')
    readonly_fields = ('enrolled_at',)

    @admin.display(description='Progreso')
    def progress_bar(self, obj):
        color = '#9fe870' if obj.progress >= 100 else '#3b82f6'
        return format_html(
            '<div style="width:120px;background:#e5e7eb;border-radius:999px;height:8px;">'
            '<div style="width:{}%;background:{};border-radius:999px;height:8px;"></div></div>'
            ' <small>{}%</small>',
            obj.progress, color, obj.progress
        )

