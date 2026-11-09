from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Includes role-based access control (ADMIN or SALES_USER)
    and enforces unique email addresses.
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        SALES_USER = 'SALES_USER', 'Sales User'

    email = models.EmailField(unique=True, verbose_name='Email Address')
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SALES_USER,
        verbose_name='User Role'
    )

    REQUIRED_FIELDS = ['email']

    @property
    def is_admin(self) -> bool:
        """Check if user has Admin role or superuser status."""
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_sales_user(self) -> bool:
        """Check if user has Sales User role."""
        return self.role == self.Role.SALES_USER

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
