from courses.models import Enrollment, Course


def nav_my_courses(request):
    """Inyecta los cursos inscritos del usuario para el menú superior."""
    if not request.user.is_authenticated:
        return {'nav_my_courses': []}
    courses = (
        Course.objects
        .filter(enrollments__student=request.user, is_published=True)
        .order_by('title')
        .only('title', 'slug', 'emoji')
    )
    return {'nav_my_courses': list(courses)}


def site_config(request):
    """Inyecta SiteConfig en todos los templates."""
    from accounts.models import SiteConfig
    return {'site_config': SiteConfig.get()}
