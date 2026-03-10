# accounts/management/commands/set_admin_role.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Set admin role for superusers'

    def handle(self, *args, **options):
        admin_users = User.objects.filter(is_superuser=True)
        for user in admin_users:
            if user.role != User.ADMIN:
                user.role = User.ADMIN
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {user.username} to admin role')
                )
        self.stdout.write(
            self.style.SUCCESS('Admin roles updated successfully')
        )