from courses.models import Enrollment, Course


def nav_my_courses(request):
    """Inyecta cursos inscritos y contadores de nav para el sidebar."""
    if not request.user.is_authenticated:
        return {'nav_my_courses': [], 'nav_courses_count': 0, 'nav_teachers_count': 0}
    enrollments = Enrollment.objects.filter(student=request.user)
    courses = (
        Course.objects
        .filter(enrollments__student=request.user, is_published=True)
        .order_by('title')
        .only('title', 'slug', 'emoji')
    )
    course_list = list(courses)
    teachers_count = (
        Course.objects
        .filter(enrollments__student=request.user, is_published=True)
        .values('instructor_id')
        .distinct()
        .count()
    )
    return {
        'nav_my_courses':     course_list,
        'nav_courses_count':  len(course_list),
        'nav_teachers_count': teachers_count,
    }


def site_config(request):
    """Inyecta SiteConfig en todos los templates."""
    from accounts.models import SiteConfig
    return {'site_config': SiteConfig.get()}


def current_app_version(request):
    """Inyecta la versión actual de la plataforma."""
    from accounts.models import AppVersion
    try:
        v = AppVersion.objects.filter(is_current=True).first()
    except Exception:
        v = None
    return {'current_app_version': v}
