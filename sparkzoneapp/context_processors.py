from .models import User

def auth_user_context(request):
    """
    Context processor to ensure user and user.role are available
    in the session/auth context across the entire application without
    needing to re-fetch on every template.
    """
    uid = request.session.get('user_id')
    user = None
    role = request.session.get('role')

    if uid:
        try:
            user = User.objects.select_related('provider_profile').get(id=uid)
            if not role or role != user.role:
                role = user.role
                request.session['role'] = role
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('role', None)
            role = None

    return {
        'logged_in_user': user,
        'user': user,
        'user_role': role,
    }
