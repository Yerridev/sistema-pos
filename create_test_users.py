import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

users = [
    ('admin',  'admin123',  'admin'),
    ('cajero', 'cajero123', 'cajero'),
]

for username, password, rol in users:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'rol': rol}
    )
    if created or not user.has_usable_password():
        user.set_password(password)
        user.save()
        print(f'Created/Updated: {username} (rol: {rol})')
    else:
        if user.rol != rol:
            user.rol = rol
            user.save()
            print(f'Updated rol: {username} -> {rol}')
        else:
            print(f'User exists: {username} (rol: {rol})')

print('\nUsers in DB:')
for u in User.objects.all():
    print(f'  - {u.username} (rol: {u.rol})')
