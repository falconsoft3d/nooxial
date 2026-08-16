from django.shortcuts import redirect
from django.urls import reverse


# Rutas que siempre se permiten aunque la pantalla esté bloqueada
_ALLOWED_PATHS = None


def _get_allowed():
    global _ALLOWED_PATHS
    if _ALLOWED_PATHS is None:
        _ALLOWED_PATHS = {
            reverse('accounts:lock_screen'),
            reverse('accounts:lock'),
            reverse('accounts:unlock'),
            reverse('accounts:logout'),
        }
    return _ALLOWED_PATHS


# Rutas exentas de T&C
_TC_EXEMPT = None


def _get_tc_exempt():
    global _TC_EXEMPT
    if _TC_EXEMPT is None:
        _TC_EXEMPT = {
            reverse('accounts:accept_terms'),
            reverse('accounts:logout'),
            reverse('accounts:lock_screen'),
            reverse('accounts:lock'),
            reverse('accounts:unlock'),
        }
    return _TC_EXEMPT


class LockScreenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.session.get('screen_locked')
            and request.path not in _get_allowed()
            and not request.path.startswith('/static/')
            and not request.path.startswith('/media/')
        ):
            return redirect('accounts:lock_screen')
        return self.get_response(request)


class TermsMiddleware:
    """Redirige a aceptar T&C si el usuario no los ha aceptado."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.path not in _get_tc_exempt()
            and not request.path.startswith('/static/')
            and not request.path.startswith('/media/')
            and not request.path.startswith('/accounts/panel/')
        ):
            from accounts.models import TermsConditions, TermsAcceptance
            active = TermsConditions.get_active()
            if active:
                already = TermsAcceptance.objects.filter(
                    user=request.user, terms=active
                ).exists()
                if not already:
                    return redirect('accounts:accept_terms')
        return self.get_response(request)

