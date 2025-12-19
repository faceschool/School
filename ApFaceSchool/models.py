from contextlib import nullcontext
from enum import unique
from typing import Any
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.dateformat import DateFormat
from .models import *
from ApFaceSchool.utils import *
from django.contrib.auth.models import AbstractUser
from PrjtEcole import settings
import secrets
import string
from django.contrib.auth.tokens import PasswordResetTokenGenerator


User = settings.AUTH_USER_MODEL
# from .models import Visitor
# User = get_user_model()
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
import uuid

class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.user.username}: {self.message[:20]}"

class Visitor(models.Model):
    ip_address = models.GenericIPAddressField()
    date_visite = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.ip_address} le {self.date_visite}"

    @staticmethod
    def visiteurs_uniques_expiration(hours=24):
        limite = timezone.now() - timedelta(hours=hours)
        return Visitor.objects.filter(date_visite__gte=limite).count()



class ActivationToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiration = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = generated_token()  # Génère un token alphanumérique unique
        if not self.expiration:
            self.expiration = timezone.now() + timedelta(hours=24)  # Token valide 24h
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expiration

    def _str_(self):
        return f"ActivationToken(user={self.user}, token={self.token})"


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('formateur', 'Formateur'),
        ('apprenant', 'Apprenant'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)


# Create your models here.
class Discipline(models.Model):
    discipline = models.CharField(max_length=50, primary_key=True)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return self.discipline


#Niveau classe ou eleve
class Niveau(models.Model):
    niveau = models.CharField(max_length=25, primary_key=True)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return f'{self.niveau}'


class TypeDocument(models.Model):
    TypeDoc = models.CharField(max_length=25, primary_key=True)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return f'{self.TypeDoc}'


class Formateurs(models.Model):
    Sex_Choix = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]

    Choix_discipline = [
        ('Mathematique', 'Mathematique'),
        ('Anglais', 'Anglais'),
        ('Français', 'Français'),
        ('Physique', 'Physique'),
        ('Allemand', 'Allemand'),
    ]

    Matricule = models.CharField(max_length=15, primary_key="true")
    Login = models.CharField(max_length=25, unique="true")
    Nom = models.CharField(max_length=15)
    Prenom = models.CharField(max_length=25)
    Email = models.EmailField(max_length=50, unique="true")
    DateNaissance = models.DateField(blank="True")
    Tel = models.CharField(max_length=20, blank="True")
    Discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True)
    Type = models.CharField(max_length=20)
    Pays = models.CharField(max_length=20)
    Sexe = models.CharField(max_length=1, choices=Sex_Choix)
    Effectif = models.IntegerField(default=0, null=True)
    username = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    CodeAutorisation = models.CharField(max_length=8, unique="true", default=CodeAutorisation())
    CodeEnregistrement = models.CharField(max_length=8)
    QuotaDossier=models.BigIntegerField(default=1048576,blank="True")  #4 294 967 296 octet
    Photo = models.FileField(upload_to=photo, blank="True",default='/static/images/default_avatar.png', null=True)  # dossier dans MEDIA
    create_at = models.DateTimeField(
        auto_now_add=True)

    class Meta :
        verbose_name = "Formateur"
        verbose_name_plural = "Formateurs"
        ordering = ['create_at']

    def __str__(self):
        return f"{self.Login}-{self.Email}"

    # Limite de taille de Fichier
    def quota_bytes(self):
        return self.QuotaDossier

    def tailledossier_utilisee(user):
        total = MesDossiers.objects.filter(username_id=user).aggregate(Sum('taille'))['taille__sum']
        return total or 0

    def espace_restant(self):
        return self.quota_bytes() - self.tailledossier_utilisee()

    def quota_atteint(self):
        return self.espace_restant() <= 0

    def pourcentage_utilise(self):
        return round((self.tailledossier_utilisee() * 100) / self.quota_bytes(), 2)




class Apprenants(models.Model):
    Sex_Choix = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    Choix_niveau = [
        ('6EME', '6EME'),
        ('5EME', '5EME'),
        ('4EME', '4EME'),
        ('3EME', '3EME'),
        ('2ND-A', '2ND-A'),
        ('2ND-C', '2ND-C'),
        ('1ER-A', '1ER-A'),
        ('1ER-C', '1ER-C'),
        ('1ER-D', '1ER-D'),
        ('TLE-A', 'TLE-A'),
        ('TLE-D', 'TLE-D'),
        ('TLE-C', 'TLE-C'),
        ('TLE-E', 'TLE-E'),
        ('TLE-F', 'TLE-F'),
    ]
    User = get_user_model()
    Matricule = models.CharField(max_length=15, primary_key="true")
    Login = models.CharField(max_length=25, unique="true")
    Email = models.EmailField(max_length=50, unique="true")
    Nom = models.CharField(max_length=15)
    Prenom = models.CharField(max_length=25)
    DateNaissance = models.DateField(blank="True")
    Tel = models.CharField(max_length=20, blank="True")
    Niveau = models.CharField(max_length=20, choices=Choix_niveau)
    CodeEts = models.CharField(max_length=10)
    Type = models.CharField(max_length=20)
    Pays = models.CharField(max_length=20)
    Sexe = models.CharField(max_length=1, choices=Sex_Choix, default='M')
    Effectif = models.IntegerField(default=0, null=True)
    username = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    CodeAutorisation = models.CharField(max_length=8,unique="true",default=CodeAutorisation())
    CodeEnregistrement = models.CharField(max_length=8)
    QuotaDossier = models.BigIntegerField(default=1048576, blank="True")  #4 294 967 296 octet
    Photo = models.FileField(upload_to=photo, blank="True", default='/static/images/default_avatar.png', null=True)  # dossier dans MEDIA
    DateDuJour = models.DateField(blank="True",null=True)
    Delai = models.IntegerField(default=45)
    actif = models.BooleanField(default=True)
    create_at = models.DateTimeField(
        auto_now_add=True)


    class Meta :
        verbose_name = "Apprenant"
        verbose_name_plural = "Apprenants"
        ordering = ['create_at']

    def __str__(self):
        return f"{self.Login}-{self.Email}"
# Limite de taille de Fichier
    def quota_bytes(self):
        return self.QuotaDossier

    def tailledossier_utilisee(user):
        total = MesDossiers.objects.filter(username_id=user).aggregate(Sum('taille'))['taille__sum']
        return total or 0

    def espace_restant(self):
        return self.quota_bytes() - self.tailledossier_utilisee()

    def quota_atteint(self):
        return self.espace_restant() <= 0

    def pourcentage_utilise(self):
        return round((self.tailledossier_utilisee() * 100) / self.quota_bytes(), 2)

class MaClasse(models.Model):
    Choix_niveau = [
        ('6EME', '6EME'),
        ('5EME', '5EME'),
        ('4EME', '4EME'),
        ('3EME', '3EME'),
        ('2ND-A', '2ND-A'),
        ('2ND-C', '2ND-C'),
        ('1ER-A', '1ER-A'),
        ('1ER-C', '1ER-C'),
        ('1ER-D', '1ER-D'),
        ('TLE-A', 'TLE-A'),
        ('TLE-D', 'TLE-D'),
        ('TLE-C', 'TLE-C'),
        ('TLE-E', 'TLE-E'),
        ('TLE-F', 'TLE-F'),
    ]
    User = get_user_model()
    NomClasse = models.CharField(max_length=20)
    CodeEts = models.CharField(max_length=30)
    Effectif = models.IntegerField(default=0)
    ChefClasse = models.CharField(max_length=30)
    CodeAffect = models.CharField(max_length=10, unique=True)
    Niveau = models.CharField(max_length=20, choices=Choix_niveau)
    Login = models.CharField(max_length=25)
    QuotaDossier = models.BigIntegerField(default=1048576, blank="True")
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return f'{self.NomClasse}'

# Limite de taille de Fichier
    def quota_bytes(self):
        return self.QuotaDossier

    def tailledossier_utilisee(user):
        total = MesDocuments.objects.filter(username_id=user).aggregate(Sum('taille'))['taille__sum']
        return total or 0

    def espace_restant(self):
        return self.quota_bytes() - self.tailledossier_utilisee()

    def quota_atteint(self):
        return self.espace_restant() <= 0

    def pourcentage_utilise(self):
        return round((self.tailledossier_utilisee() * 100) / self.quota_bytes(), 2)
#Partenariat entre Classe
class PartenariatClasse(models.Model):
    ClassDemandeur = models.ForeignKey(MaClasse, on_delete=models.CASCADE, related_name='demandeurs')
    ClassPartenaire = models.ForeignKey(MaClasse, on_delete=models.CASCADE, related_name='partenaires')
    ProfDemandeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='demandeursProf')
    ProfPartenaire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partenairesprof')
    create_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['ClassDemandeur', 'ClassPartenaire'], name='ClassePartenaire')
        ]


class MesDocuments(models.Model):
    # def __init__(self, *args: Any, **kwargs: Any):
    #  super().__init__(args, kwargs)
    # self.Maclasse = None

    Choix_discipline = [
        ('Mathematique', 'Mathematique'),
        ('Anglais', 'Anglais'),
        ('Français', 'Français'),
        ('Physique', 'Physique'),
        ('Allemand', 'Allemand'),
    ]

    Choix_niveau = [
        ('6EME', '6EME'),
        ('5EME', '5EME'),
        ('4EME', '4EME'),
        ('3EME', '3EME'),
        ('2ND-A', '2ND-A'),
        ('2ND-C', '2ND-C'),
        ('1ER-A', '1ER-A'),
        ('1ER-C', '1ER-C'),
        ('1ER-D', '1ER-D'),
        ('TLE-A', 'TLE-A'),
        ('TLE-D', 'TLE-D'),
        ('TLE-C', 'TLE-C'),
        ('TLE-E', 'TLE-E'),
        ('TLE-F', 'TLE-F'),
    ]

    Choix_TypeDoc = [
        ('Cours', 'Cours'),
        ('Devoirs', 'Devoirs'),
        ('Exercices', 'Exercices'),
        ('Epreuve', 'Epreuve'),
        ('Exposé', 'Exposé'),
    ]
    Choix_Etat = [
        ('PRIVE', 'PRIVE'),
        ('PUBLIC', 'PUBLIC'),
    ]
    User = get_user_model()
    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    Discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True)
    Niveau = models.CharField(max_length=20, choices=Choix_niveau)
    Titre = models.CharField(max_length=50)
    TypeDoc = models.CharField(max_length=20, choices=Choix_TypeDoc)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Observation = models.TextField(blank=True)
    Document = models.FileField(upload_to=documents_Classe)  # dossier dans MEDIA
    taille = models.BigIntegerField(default=0)  # en octets
    Dossier_link = models.URLField(blank=True,null=True)
    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)


class MesDossiers(models.Model):
    # def __init__(self, *args: Any, **kwargs: Any):
    #  super().__init__(args, kwargs)
    # self.Maclasse = None
    #models=TypeDocument
    Choix_Etat = [
        ('PRIVE', 'PRIVE'),
        ('PUBLIC', 'PUBLIC'),
    ]
    User = get_user_model()
    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    Niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    Titre = models.CharField(max_length=50)
    TypeDoc = models.ForeignKey(TypeDocument, on_delete=models.CASCADE)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Observation = models.TextField(blank=True)
    Document = models.FileField(upload_to=dossier_form)  # dossier dans MEDIA
    taille = models.BigIntegerField(blank=True, null=True) # en octets
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    Dossier_link = models.URLField(blank=True,null=True)
    create_at = models.DateTimeField(
        auto_now_add=True)


class apprenant_maclasses(models.Model):
    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    apprenant = models.ForeignKey(Apprenants, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:
        unique_together = ('maclasse', 'apprenant')  # clé composée simulée

        # constraints = [
        #    models.UniqueConstraint(fields=['maclasse', 'apprenant'], name='ClasseApprenant')
    # ]


class SoluExoClasses(models.Model):
    Choix_Etat = [
        ('PRIVE', 'PRIVE'),
        ('PUBLIC', 'PUBLIC'),
    ]

    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    Niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    Solution = models.FileField(upload_to=Solution_doc)  # dossier dans MEDIA
    taille = models.BigIntegerField(default=0)  # en octets
    Contenu = models.TextField(blank=True)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Note = models.CharField(max_length=5,default='',blank=True)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    documents = models.ForeignKey(MesDocuments, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:
        #unique_together = ('maclasse', 'apprenant')  # clé composée simulée

        constraints = [
            models.UniqueConstraint(fields=['username', 'documents'], name='SolutionDocuments')
        ]


class GroupeTravails(models.Model):

    Groupe = models.CharField(max_length=25)
    Responsable = models.CharField(max_length=30, null=True, blank=True)
    Contact = models.TextField(blank=True)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    logo = models.FileField(upload_to=GroupeTravail)
    QuotaDossier=models.BigIntegerField(default=1048576,blank="True")
    CodeAffect = models.CharField(max_length=10, unique=True)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return self.Groupe

# Limite de taille de Fichier
    def quota_bytes(self):
        return self.QuotaDossier

    def tailledossier_utilisee(user):
        total = DossiersGRPTrav.objects.filter(username_id=user).aggregate(Sum('taille'))['taille__sum']
        return total or 0

    def espace_restant(self):
        return self.quota_bytes() - self.tailledossier_utilisee()

    def quota_atteint(self):
        return self.espace_restant() <= 0

    def pourcentage_utilise(self):
        return round((self.tailledossier_utilisee() * 100) / self.quota_bytes(), 2)

class form_grpe_travails(models.Model):
    Matricule = models.ForeignKey(Formateurs, on_delete=models.CASCADE)
    groupetravail = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['Matricule', 'groupetravail'], name='groupetravailFormateur')
        ]


#Documents Groupe de Travail
class DossiersGRPTrav(models.Model):
    # def __init__(self, *args: Any, **kwargs: Any):
    #  super().__init__(args, kwargs)
    # self.Maclasse = None
    #models=TypeDocument
    Choix_Etat = [
        ('PRIVE', 'PRIVE'),
        ('PUBLIC', 'PUBLIC'),
    ]

    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    groupetravail = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    Niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    Titre = models.CharField(max_length=50)
    TypeDoc = models.ForeignKey(TypeDocument, on_delete=models.CASCADE)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Observation = models.TextField(blank=True)
    Document = models.FileField(upload_to=DocGroupeTravail)  # dossier dans MEDIA
    taille = models.BigIntegerField(default=0)  # en octets
    Dossier_link = models.URLField(blank=True,null=True)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)


class PartenariatGroupTrav(models.Model):
    GroupeTravDemandeur = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE, related_name='demandeurs')
    GroupeTravPartenaire = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE, related_name='partenaires')
    ProfsDemandeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='demandeursProfs')
    ProfsPartenaire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partenairesprofs')
    create_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['GroupeTravDemandeur', 'GroupeTravPartenaire'], name='GroupeTravPartenaire')
        ]

# Groupe etude

class GroupeEtude(models.Model):
    #User = get_user_model()
    Groupe = models.CharField(max_length=25)
    Responsable = models.CharField(max_length=30, null=True, blank=True)
    Contact = models.TextField(blank=True)
    Etablissement = models.CharField(max_length=30)
    Niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    CodeAffect = models.CharField(max_length=10, unique=True)
    QuotaDossier = models.BigIntegerField(default=1048576, blank="True")
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    logo = models.FileField(upload_to=GroupeEtude)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return self.Groupe
# Limite de taille de Fichier
    def quota_bytes(self):
        return self.QuotaDossier

    def tailledossier_utilisee(user):
        total = DossiersGRPEtude.objects.filter(username_id=user).aggregate(Sum('taille'))['taille__sum']
        return total or 0

    def espace_restant(self):
        return self.quota_bytes() - self.tailledossier_utilisee()

    def quota_atteint(self):
        return self.espace_restant() <= 0

    def pourcentage_utilise(self):
        return round((self.tailledossier_utilisee() * 100) / self.quota_bytes(), 2)

class Appren_GroupeEtude(models.Model):
    Matricule = models.ForeignKey(Apprenants, on_delete=models.CASCADE)
    groupetude = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['Matricule', 'groupetude'], name='groupeetudeapprenant')
        ]


#Documents Groupe de Etude
class DossiersGRPEtude(models.Model):

    Choix_Etat = [
        ('PRIVE', 'PRIVE'),
        ('PUBLIC', 'PUBLIC'),
    ]

    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    groupetude = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    Niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    Titre = models.CharField(max_length=50)
    TypeDoc = models.ForeignKey(TypeDocument, on_delete=models.CASCADE)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Observation = models.TextField(blank=True)
    Document = models.FileField(upload_to=DocGroupeEtude)  # dossier dans MEDIA
    taille = models.BigIntegerField(default=0)  # en octets
    Dossier_link = models.URLField(blank=True,null=True)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)


class PartenariatGroupEtude(models.Model):
    GroupeEtudDemandeur = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE, related_name='demandeurs')
    GroupeEtudPartenaire = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE, related_name='partenaires')
    ApprenDemandeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='demandeursAppre')
    ApprenPartenaire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partenairesAppre')
    Auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['GroupeEtudDemandeur', 'GroupeEtudPartenaire'], name='GroupeEtudePartenaire')
        ]


# MESSAGE CLASSE
class Message_Classes(models.Model):
    #User = get_user_model()
    Objet = models.CharField(max_length=100)
    Message = models.TextField(blank=True)
    PiecesJointe = models.FileField(upload_to=MessageClasse, blank=True)
    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)


class Message_GroupeTravail(models.Model):

    Objet = models.CharField(max_length=100)
    Message = models.TextField(blank=True)
    PiecesJointe = models.FileField(upload_to=MessGroupeTravail)
    groupetravail = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)


class Message_GroupeEtude(models.Model):
    User = get_user_model()
    Objet = models.CharField(max_length=100)
    Message = models.TextField(blank=True)
    PiecesJointe = models.FileField(upload_to=MessageGroupeEtude)
    groupeetude = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE)
    username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)


class SujetDiscussion(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)


class MessageDiscussion(models.Model):

    sujet = models.ForeignKey(SujetDiscussion, related_name="messages", on_delete=models.CASCADE)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_post = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.auteur} - {self.date_post}"

#Meeting

class Reunion(models.Model):

    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    titre = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    formateurs = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reunions_formateur')
    apprenants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='reunions_apprenant')
    meet_link = models.URLField(blank=True)
    etat=models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)
    def str(self):
        return f"{self.titre} ({self.date_debut.strftime('%d/%m/%Y %H:%M')})"

# Reunion Groupe Etude
class ReunionEtude(models.Model):

    groupeetude = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE)
    titre = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    apprenants = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reunionAppren')
    meet_link = models.URLField(blank=True)
    etat=models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)

# Reunion Groupe de travail
class ReunionGrpTravail(models.Model):

    groupetravail = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE)
    titre = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    formateurs = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reunionsformateur')
    meet_link = models.URLField(blank=True)
    etat=models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)

# Publicité
class Publicite(models.Model):
    titre = models.CharField(max_length=100)
    image = models.ImageField(upload_to='publicites/')
    lien = models.URLField()
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.titre

class CoursAdomicile(models.Model):
    titre = models.CharField(max_length=100)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE,blank=True, null=True)
    image = models.ImageField(upload_to='CoursAdomiciles/')
    taille = models.BigIntegerField(default=0)  # en octets
    description = models.TextField()
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.titre

# Publicité
class CentreFormation(models.Model):
    NomEtablissement = models.CharField(max_length=50)
    description = models.TextField()
    Logo = models.ImageField(upload_to='Ecole_form')
    lien = models.URLField()
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.NomEtablissement

# Activation de compte
class Activation(models.Model):
    Matricule = models.ForeignKey(Apprenants, on_delete=models.CASCADE)
    CodeActivation = models.CharField(max_length=10,unique=True)
    Delais=models.IntegerField(default=365)
    Etat = models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)

class QuotaRequest(models.Model):
    PAYMENT_NONE = "none"
    PAYMENT_PENDING = "pending"
    PAYMENT_OK = "paid"
    PAYMENT_FAILED = "failed"

    STATUS_NEW = "new"          # demande créée (admin non traitée)
    STATUS_APPROVED = "approved" # admin approuvé (sans paiement)
    STATUS_REJECTED = "rejected" # admin refusé
    STATUS_WAITING_PAYMENT = "waiting_payment" # attente paiement
    STATUS_PAID = "paid"        # paiement validé + admin validation possible

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quota_requests")
    requested_gb = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default=STATUS_NEW)
    payment_status = models.CharField(max_length=32, default=PAYMENT_NONE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_provider = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=200, blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"QuotaRequest#{self.pk} user={self.user} {self.requested_gb}GB status={self.status}"
