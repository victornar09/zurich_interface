from django.db import models

# Create your models here.

class SoloLecturaModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        raise Exception("Operación no permitida: solo lectura")

# Luego, usa SoloLecturaModel como base para tus modelos
class MiModelo(SoloLecturaModel):
    campo1 = models.CharField(max_length=100)