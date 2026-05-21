from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('cajero', 'Cajero'),
    ]
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='cajero')

    def __str__(self):
        return f"{self.username} ({self.rol})"
