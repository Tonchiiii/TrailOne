from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from authentication.models import Users

class Command(BaseCommand):
    help = 'Seed the Users table with sample data'

    def handle(self, *args, **kwargs):
        users_data = [
            {
                'name': 'Lorelie Canete',
                'role': 'SUPER_ADMIN',
                'email': 'lorie@trailone.com',
                'password_hash': make_password('password'),
            },
            {
                'name': 'Charlie Brown',
                'role': 'ADMIN',
                'email': 'charlie@trailone.com',
                'password_hash': make_password('password'),
            },
            {
                'name': 'Bob Smith',
                'role': 'CLIENT',
                'email': 'bob@trailone.com',
                'password_hash': make_password('password'),
            },
            {
                'name': 'Rey Ban',
                'role': 'CLIENT',
                'email': 'rey@trailone.com',
                'password_hash': make_password('password'),
            },
            {
                'name': 'John Doe',
                'role': 'CLIENT',
                'email': 'john@trailone.com',
                'password_hash': make_password('password'),
            },
        ]

        for user in users_data:
            # Log the password hash before saving it
            self.stdout.write(f"Creating user with email {user['email']} and password hash {user['password_hash']}")

            Users.objects.update_or_create(
                email=user['email'],
                defaults=user,
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded Users table.'))
