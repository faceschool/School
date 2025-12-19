from django.contrib import admin
from .models import *


# Register your models here.

class FormateursAdmin(admin.ModelAdmin):
    list_display = ('Login', 'Matricule', 'Nom', 'Prenom', 'Email','QuotaDossier', 'create_at')
    list_filter = ('Nom', 'create_at')
    search_fields = ("user__username",)


class ApprenantAdmin(admin.ModelAdmin):
    list_display = ('Login', 'Matricule', 'Nom', 'Prenom', 'Email','QuotaDossier', 'create_at')
    list_filter = ('Nom', 'create_at')
    search_fields = ("user__username",)

class NiveauAdmin(admin.ModelAdmin):
    list_display = ('niveau','create_at')


class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('discipline', 'create_at')


class TypeDocAdmin(admin.ModelAdmin):
    list_display = ('TypeDoc','create_at')

admin.site.register(Formateurs, FormateursAdmin)
admin.site.register(Apprenants, FormateursAdmin)
admin.site.register(Niveau, NiveauAdmin)
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TypeDocument, TypeDocAdmin)




