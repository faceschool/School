from contextlib import nullcontext
from enum import unique
from typing import Any

from django.db import models
from django.contrib.auth.models import User
from django.utils.dateformat import DateFormat
from ApFaceSchool.utils import *
from django.contrib.auth.models import AbstractUser

#from ApFaceSchool.utils import dossier_form


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
    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    #Discipline = models.CharField(max_length=20)
    Discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True)
    Type = models.CharField(max_length=20)
    Pays = models.CharField(max_length=20)
    Sexe = models.CharField(max_length=1, choices=Sex_Choix)
    Effectif = models.IntegerField(default=0, null=True)
    username = models.OneToOneField(User, on_delete=models.CASCADE)
    Photo = models.FileField(upload_to=photo,blank="True",null=True)  # dossier dans MEDIA
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return f"{self.Login}-{self.Email}"


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
    username = models.OneToOneField(User, on_delete=models.CASCADE)
    Photo = models.FileField(upload_to=photo,blank="True",null=True)  # dossier dans MEDIA
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return f"{self.Login}-{self.Email}"


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
    NomClasse = models.CharField(max_length=20)
    CodeEts = models.CharField(max_length=30)
    Effectif = models.IntegerField(default=0)
    ChefClasse = models.CharField(max_length=30)
    CodeAffect = models.CharField(max_length=10, unique=True)
    Niveau = models.CharField(max_length=20, choices=Choix_niveau)
    Login = models.CharField(max_length=25)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return f'{self.NomClasse}'

#Partenariat entre Classe
class PartenariatClasse(models.Model):

        ClassDemandeur = models.ForeignKey(MaClasse, on_delete=models.CASCADE, related_name='demandeurs')
        ClassPartenaire = models.ForeignKey(MaClasse, on_delete=models.CASCADE, related_name='partenaires')
        ProfDemandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandeursProf')
        ProfPartenaire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='partenairesprof')
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
    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    Discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True)
    Niveau = models.CharField(max_length=20, choices=Choix_niveau)
    Titre = models.CharField(max_length=50)
    TypeDoc = models.CharField(max_length=20, choices=Choix_TypeDoc)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Observation = models.TextField(blank=True)
    Document = models.FileField(upload_to=documents_Classe)  # dossier dans MEDIA
    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
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
    #Discipline = models.CharField(max_length=20, choices=Choix_discipline)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    Niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    Titre = models.CharField(max_length=50)
    TypeDoc = models.ForeignKey(TypeDocument, on_delete=models.CASCADE)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Observation = models.TextField(blank=True)
    Document = models.FileField(upload_to=dossier_form)  # dossier dans MEDIA
    username = models.ForeignKey(User, on_delete=models.CASCADE)
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
    Contenu = models.TextField(blank=True)
    Etat = models.CharField(max_length=10, choices=Choix_Etat)
    Note=models.CharField(max_length=5)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    documents= models.ForeignKey(MesDocuments, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:
        #unique_together = ('maclasse', 'apprenant')  # clé composée simulée

           constraints = [
                models.UniqueConstraint(fields=['username', 'documents'], name='SolutionDocuments')
        ]


class GroupeTravails(models.Model):
    Groupe = models.CharField(max_length=25)
    Responsable = models.CharField(max_length=30,null=True,blank=True)
    Contact = models.TextField(blank=True)
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    logo=models.FileField(upload_to=GroupeTravail)
    #Etablissement = models.CharField(max_length=30)
    CodeAffect = models.CharField(max_length=10, unique=True)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

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
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

class PartenariatGroupTrav(models.Model):
        GroupeTravDemandeur = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE, related_name='demandeurs')
        GroupeTravPartenaire = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE, related_name='partenaires')
        ProfsDemandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandeursProfs')
        ProfsPartenaire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='partenairesprofs')
        create_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            constraints = [
                models.UniqueConstraint(fields=['GroupeTravDemandeur', 'GroupeTravPartenaire'], name='GroupeTravPartenaire')
            ]

class GroupeEtude(models.Model):
    Groupe = models.CharField(max_length=25)
    Responsable = models.CharField(max_length=30,null=True,blank=True)
    Contact = models.TextField(blank=True)
    logo=models.FileField(upload_to=GroupeEtude)
    Etablissement = models.CharField(max_length=30)
    CodeAffect = models.CharField(max_length=10, unique=True)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(
        auto_now_add=True)

class Message_Classes(models.Model):

    Objet=models.CharField(max_length=100)
    Message=models.TextField(blank=True)
    PiecesJointe = models.FileField(upload_to=MessageClasse,blank=True)
    maclasse = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)

class Message_GroupeTravail(models.Model):

    Objet=models.CharField(max_length=100)
    Message=models.TextField(blank=True)
    PiecesJointe = models.FileField(upload_to=MessGroupeTravail)
    groupetravail = models.ForeignKey(GroupeTravails, on_delete=models.CASCADE)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)


class Message_GroupeEtude(models.Model):

    Objet=models.CharField(max_length=100)
    Message=models.TextField(blank=True)
    PiecesJointe = models.FileField(upload_to=MessageGroupeEtude)
    groupeetude = models.ForeignKey(GroupeEtude, on_delete=models.CASCADE)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)



class SujetDiscussion(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)


class MessageDiscussion(models.Model):
    sujet = models.ForeignKey(SujetDiscussion, related_name="messages", on_delete=models.CASCADE)
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_post = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.auteur} - {self.date_post}"

# class CustomUser(AbstractUser):
#     ROLE_CHOICES = (
#         ('formateur', 'Formateur'),
#         ('apprenant', 'Apprenant'),
#     )
#     role = models.CharField(max_length=10, choices=ROLE_CHOICES)

class Reunion(models.Model):
    titre = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    formateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reunions_formateur')
    apprenants = models.ManyToManyField(User, related_name='reunions_apprenant')
    meet_link = models.URLField(blank=True)

