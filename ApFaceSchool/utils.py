import os
import secrets

from django.db.models.aggregates import Sum
from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta
import string

from ApFaceSchool.models import *

# Creer un Dossier de stockage en fonction de l'année et le nom utilisateur

def dossier_form(instance, filename):
    discipline = str(instance.Discipline.discipline).replace(' ', '_') if instance.Discipline else 'Indefini'
    niveaux = str(instance.Niveau).replace(' ', '_') if instance.Niveau else 'Indefini'
    return os.path.join('dossFormateur', str(now().year), discipline, niveaux, instance.username.username, filename)

def documents_Classe(instance, filename):
    discipline = str(instance.Discipline.discipline).replace(' ', '_') if instance.Discipline else 'Indefini'
    niveaux = str(instance.Niveau).replace(' ', '_') if instance.Niveau else 'Indefini'
    return os.path.join('docClasse', str(now().year), discipline, niveaux, instance.username.username, filename)

def Solution_doc(instance, filename):
    discipline = str(instance.Discipline.discipline).replace(' ', '_') if instance.Discipline else 'Indefini'
    niveaux = str(instance.Niveau).replace(' ', '_') if instance.Niveau else 'Indefini'
    return os.path.join('Solution', str(now().year), discipline, niveaux, instance.username.username, filename)

#Voici un exemple de fonction chemin_upload personnalisée qui range les fichiers par discipline, classe, et nom d’utilisateur :

def dossier_appren(instance, filename):
    # On sécurise les noms au cas où certains contiennent des espaces ou caractères spéciaux
    niveaux = str(instance.Niveau).replace(' ', '_') if instance.Niveau else 'Indefini'
    discipline = str(instance.Discipline.discipline).replace(' ', '_') if instance.Discipline else 'Indefini'
    #classe = str(instance.maclasse.NomClasse).replace(' ', '_') if instance.maclasse else 'Classe'
    utilisateur = str(instance.username.username)
    return os.path.join('docClasse', str(now().year),discipline, niveaux, utilisateur, filename)

def photo(instance, filename):
    return os.path.join('photo', str(now().year),instance.username.username, filename)

def GroupeTravail(instance, filename):
    return os.path.join('GroupeTravail/logo', str(now().year),instance.username.username, filename)

def GroupeEtude(instance, filename):
    return os.path.join('GroupeEtude/logo', str(now().year),instance.username.username, filename)
def DocGroupeEtude(instance, filename):
    discipline = str(instance.Discipline.discipline).replace(' ', '_') if instance.Discipline else 'Indefini'
    return os.path.join('GroupeEtude/Documents', str(now().year),discipline,instance.username.username, filename)

# Les messages
def MessGroupeTravail(instance, filename):
    return os.path.join('Messages/GroupeTravail/Pieces', str(now().year),instance.username.username, filename)
def MessageGroupeEtude(instance, filename):
    return os.path.join('Messages/GroupeEtude/Pieces', str(now().year),instance.username.username, filename)
def MessageClasse(instance, filename):
    return os.path.join('Messages/MessClasse/Pieces', str(now().year),instance.username.username, filename)

def DocGroupeTravail(instance, filename):
    discipline = str(instance.Discipline.discipline).replace(' ', '_') if instance.Discipline else 'Indefini'
    return os.path.join('GroupeTravail/Documents', str(now().year),discipline,instance.username.username, filename)

# ecole
def Ecole_form(instance, filename):
    Etablissement = str(instance.CentreFormation).replace(' ', '_') if instance.CentreFormation else 'Indefini'
    return os.path.join('Ecole', str(now().year), Etablissement, instance.username.username, filename)



# Fonction utilitaire pour générer un token
def generated_token(length=64):
    return secrets.token_hex(length // 2)

# Fonction utilitaire pour générer un code token
def generated_code(length=10):
    return secrets.token_hex(length // 2)

# Fonction utilitaire pour générer un code autorisation
def CodeAutorisation(length=8):
    alphabet = string.digits
    code_aleatoire = ''.join(secrets.choice(alphabet) for _ in range(length))
    return code_aleatoire

def taillefichier(fichier):
    total = fichier.size
    return total or 0

