
from django.contrib.auth.forms import UserCreationForm
from django.template.defaultfilters import default
import re
from ApFaceSchool.models import *
#from ApFaceSchool.forms import *

from .models import MesDocuments

from .models import MessageDiscussion, SujetDiscussion
from django.contrib.auth.models import AbstractUser
from ApFaceSchool.models import CustomUser  # Adapte le chemin si nécessaire
from .models import Reunion
from django import forms
from django.core.exceptions import ValidationError
from .models import Apprenants
import os

class FormulaireInscription(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']


# Formulaire Formateur
class ProfilFormateursForm(forms.ModelForm):
    class Meta:
        model = Formateurs
        exclude = ['create_at', 'username', 'Type', 'Matricule', 'Login','Effectif','Email','CodeAutorisation','CodeEnregistrement']
        widgets = {
            'Nom': forms.TextInput(attrs={'class': 'form-control'}),
            'Prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'Tel': forms.TextInput(attrs={'class': 'form-control'}),
            'Email': forms.EmailInput(attrs={'class': 'form-control'}),
            'Sexe': forms.Select(attrs={'class': 'form-select'}),
            'Discipline': forms.Select(attrs={'class': 'form-select'}),
            'Pays': forms.TextInput(attrs={'class': 'form-control'}),
            'CodeEnregistrement': forms.TextInput(attrs={'class': 'form-control'}),
            'CodeAutorisation': forms.TextInput(attrs={'class': 'form-control'}),
            'Effectif': forms.TextInput(attrs={'class': 'form-control'}),
            'DateNaissance': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            "Photo": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ".jpg,.jpeg,.png"
            }),
        }
        labels = {
            'Nom': 'Nom',
            'Prenom': 'Prénom',
            'Tel': 'Téléphone',
            'Email': 'Email',
            'Sexe': 'Sexe',
            'DateNaissance': 'Date de naissance',
            'Discipline': 'Discipline',
            'Pays': 'Pays',
            'CodeEnregistrement': 'Code d’enregistrement',
            'CodeAutorisation': 'Code d’autorisation',
            'Effectif': 'Effectif',
            'Photo': 'Photo de profil',
        }

    def clean_Tel(self):
        tel = self.cleaned_data.get("Tel", "")
        pattern = r'^\+?\d{8,15}$'
        if not re.match(pattern, tel):
            raise ValidationError("Le numéro de téléphone est invalide. Exemple : +22507000000")
        return tel

    def clean_Photo(self):
        Photo = self.cleaned_data.get("Photo")
        if Photo:
            if Photo.size > 300 * 1024:
                raise ValidationError("La photo dépasse la taille maximale autorisée (300 Ko).")
            ext = os.path.splitext(Photo.name)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png"]:
                raise ValidationError("Format d’image non autorisé. Formats acceptés : JPG, JPEG, PNG.")
        return Photo

    def clean(self):
        cleaned_data = super().clean()
        nom = cleaned_data.get("Nom")
        prenom = cleaned_data.get("Prenom")

        if nom and prenom and nom.lower() == prenom.lower():
            raise ValidationError("Le nom et le prénom ne peuvent pas être identiques.")
        return cleaned_data

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['Email'].disabled = True

# Formulaire Apprenant
class ProfilApprenantForm(forms.ModelForm):
    """
    Formulaire professionnel de mise à jour du profil apprenant.
    Gère les validations de données et la vérification de la photo (taille + extension).
    """

    # On peut aussi personnaliser le widget si nécessaire :
    DateNaissance = forms.DateField(
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",  # ou "text" si tu veux un datepicker JS
            }
        ),
        label="Date de naissance",
        required=True,
    )

    class Meta:
        model = Apprenants
        fields = [
            "Nom", "Prenom", "DateNaissance", "Tel",
            "Pays", "Sexe", "Niveau", "CodeEts", "Photo"
        ]
        labels = {
            "Nom": "Nom",
            "Prenom": "Prénom",
            "Tel": "Téléphone",
            "Pays": "Pays",
            "Sexe": "Sexe",
            "Niveau": "Niveau",
            "CodeEts": "Code établissement",
            "Photo": "Photo de profil",
            "DateNaissance": "Date de naissance",
        }


        widgets = {
            "Nom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Entrez votre nom"}),
            "Prenom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Entrez votre prénom"}),
            "Tel": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: +2250700000000"}),
            "Pays": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Côte d’Ivoire"}),
            "Sexe": forms.Select(attrs={"class": "form-select"}),
            "Niveau": forms.Select(attrs={"class": "form-select"}),
            "CodeEts": forms.TextInput(attrs={"class": "form-control", "placeholder": "Code de votre établissement"}),
            "DateNaissance" : forms.DateInput(
                    format='%d/%m/%Y',
                    attrs={
                        "class": "form-control datepicker",
                        "placeholder": "JJ/MM/AAAA",
                    }
                ),

            "Photo": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ".jpg,.jpeg,.png"
            }),
        }

    def clean_Tel(self):
        """Validation du numéro de téléphone."""
        tel = self.cleaned_data.get("Tel")
        if not tel.isdigit():
            raise ValidationError("Le numéro de téléphone ne doit contenir que des chiffres.")
        if len(tel) < 8:
            raise ValidationError("Le numéro de téléphone doit contenir au moins 8 chiffres.")
        return tel

    def clean_Photo(self):
        """Validation de la photo (taille max 300 Ko et extension valide)."""
        photo = self.cleaned_data.get("Photo")
        if photo:
            # Vérification de la taille
            if photo.size > 300 * 1024:
                raise ValidationError("La photo dépasse la taille maximale autorisée (300 Ko).")

            # Vérification de l’extension
            ext = os.path.splitext(photo.name)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png"]:
                raise ValidationError("Format d’image non autorisé. Formats acceptés : JPG, JPEG, PNG.")
        return photo
# Formulaire Classe

class ClasseForm(forms.ModelForm):
    #discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True)
    class Meta:
        model = MaClasse
        exclude = ['create_at','Login','Username'
                   ]
        fields = ['NomClasse','Niveau','ChefClasse','CodeEts',
        'CodeAffect','Effectif']

        #Niveau = forms.ModelChoiceField(
        #   queryset=Niveau.objects.all(),
        #    widget=forms.Select(attrs={'class': 'form-control'})
        #)

        widgets = {
            'NomClasse': forms.TextInput(attrs={'class': 'form-control'}),
            'Niveau': forms.Select(attrs={'class': 'form-control'}),
            'ChefClasse': forms.TextInput(attrs={'class': 'form-control'}),
            'CodeEts': forms.TextInput(attrs={'class': 'form-control'}),
            'CodeAffect': forms.TextInput(attrs={'class': 'form-control'}),
            'Effectif': forms.TextInput(attrs={'class': 'form-control'}),
            }

        labels = {
            'NomClasse': 'Classe:',
            'Niveau': 'Niveau:',
            'ChefClasse': 'Chef Classe:',
            'CodeEts': 'Code Ets:',
            'CodeAffect': 'Code Invitation:',
            'Effectif':'Effectif',
        }

# Partenariat

class PartenariatClasseForm(forms.ModelForm):
    ClassDemandeur = models.ForeignKey(MaClasse, on_delete=models.CASCADE)
    ClassPartenaire = models.IntegerField(default=False)
    ProfDemandeur = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    ProfPartenaire = models.IntegerField(default=False)
    class Meta:
        model = PartenariatClasse
        exclude = ['create_at',
                   ]
        fields = ['ClassDemandeur','ClassPartenaire','ProfDemandeur','ProfPartenaire',
        ]

        #Niveau = forms.ModelChoiceField(
        #   queryset=Niveau.objects.all(),
        #    widget=forms.Select(attrs={'class': 'form-control'})
        #)

        widgets = {
            'ClassDemandeur': forms.TextInput(attrs={'class': 'form-control'}),
            #'Niveau': forms.ModelChoiceField(queryset=Niveau.objects.all(),attrs={'class': 'form-control'}),
            'ClassPartenaire': forms.Select(attrs={'class': 'form-control'}),
            'ProfDemandeur': forms.TextInput(attrs={'class': 'form-control'}),
            'ProfPartenaire': forms.TextInput(attrs={'class': 'form-control'}),
            }

        labels = {
            'ClassDemandeur': 'Classe Demandeur:',
            'ClassPartenaire': 'Classe Partenaire:',
            'ProfDemandeur': 'Prof Demandeur:',
            'ProfPartenaire': 'Prof Partenaire:',
        }

#Message Classe
class MessageClasseForm(forms.ModelForm):

    class Meta:
        model = Message_Classes
        exclude = ['create_at','Username'
                   ]
        fields = ['Objet','Message','PiecesJointe','maclasse']

        #Niveau = forms.ModelChoiceField(
        #   queryset=Niveau.objects.all(),
        #    widget=forms.Select(attrs={'class': 'form-control'})
        #)

        widgets = {
            'Objet': forms.TextInput(attrs={'class': 'form-control'}),
            'Message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'PiecesJointe': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'maclasse': forms.TextInput(attrs={'class': 'form-control'}),

            }

        labels = {
            'Objet': 'Objet',
            'Message': 'Message',
            'PiecesJointe': 'PiecesJointe',
            'maclasse': 'maclasse',
        }


#Formulaire Documents

class MesDocumentsForm(forms.ModelForm):

    class Meta:
        model = MesDocuments
        fields = ['Discipline', 'Niveau', 'Titre', 'TypeDoc',
                  'Observation', 'Etat', 'Document']

        widgets = {
            'Observation': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'Titre': forms.TextInput(attrs={'class': 'form-control'}),
            'Document': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpeg,.jpg',
                'onchange': 'validateFileSize(this)'
            }),
            'Discipline': forms.Select(attrs={'class': 'form-control'}),
            'Niveau': forms.Select(attrs={'class': 'form-control'}),
            'TypeDoc': forms.Select(attrs={'class': 'form-control'}),
            'Etat': forms.Select(attrs={'class': 'form-control'}),
        }

        labels = {
            'Observation': 'Observation',
            'Titre': 'Titre',
            'Document': 'Document',
            'Discipline': 'Discipline',
            'Niveau': 'Niveau',
            'TypeDoc': 'Type Document',
            'Etat': 'Etat',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Document n'est pas obligatoire
        self.fields['Document'].required = False

    def clean_Document(self):
        file = self.cleaned_data.get('Document')
        if file:
            # Taille maximale: 20MB
            if file.size > 20 * 1024 * 1024:
                raise forms.ValidationError("Le fichier est trop grand (max 20MB).")

            # Vérifier l'extension
            valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpeg', '.jpg']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    "Extensions autorisées : .doc, .docx, .pdf, .xls, .xlsx, .png, .jpeg, .jpg"
                )
        return file

# Formulaire Dossiers
class MesDossiersForm(forms.ModelForm):

    class Meta:
        model = MesDossiers

        # username retiré pour éviter modification manuelle
        fields = ['Discipline', 'Niveau', 'Titre', 'TypeDoc',
                  'Observation', 'Etat', 'Document', 'Dossier_link']

        widgets = {
            'Observation': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'Titre': forms.TextInput(attrs={'class': 'form-control'}),
            'Document': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpeg,.jpg',
                'onchange': 'validateFileSize(this)'
            }),
            'Discipline': forms.Select(attrs={'class': 'form-control'}),
            'Niveau': forms.Select(attrs={'class': 'form-control'}),
            'TypeDoc': forms.Select(attrs={'class': 'form-control'}),
            'Etat': forms.Select(attrs={'class': 'form-control'}),
            'Dossier_link': forms.URLInput(attrs={'class': 'form-control'}),
        }

        labels = {
            'Observation': 'Observation',
            'Titre': 'Titre',
            'Document': 'Document',
            'Discipline': 'Discipline',
            'Niveau': 'Niveau',
            'TypeDoc': 'Type de document',
            'Etat': 'État',
            'Dossier_link': 'Lien du dossier',
        }

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # Le document est optionnel
    #     self.fields['Document'].required = False

    def clean_Document(self):
        file = self.cleaned_data.get('Document')
        if file:
            max_size = 20 * 1024 * 1024  # 20 Mo
            if file.size > max_size:
                raise forms.ValidationError("Le fichier est trop grand (max 20 Mo).")
            valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpeg', '.jpg']
            taille=file.size
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Extensions autorisées : {', '.join(valid_extensions)}"
                )
        return file

class SolutionExoForm(forms.ModelForm):


    class Meta:
        model = SoluExoClasses

        fields = ['Discipline', 'Niveau', 'Note',
                  'Etat','Solution', 'Contenu'
                  ]


        widgets = {
            'maclasse': forms.TextInput(attrs={'class': 'form-control'}),
            'Discipline':forms.Select(attrs={'class': 'form-control'}),
            'Niveau':forms.Select(attrs={'class': 'form-control'}),
            'Solution': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpeg,.jpg',
                'onchange': 'validateFileSize(this)'
            }),
            'Contenu' : forms.Textarea(attrs={'rows': 4,'class': 'form-control'}),
            'Etat': forms.Select(attrs={'class': 'form-control'}),
            'Note': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            # 'documents' : forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {

            'maclasse':'maclasse',
             'Discipline':'Discipline',
            'Niveau':'Niveau',
            'Solution' :'Solution',
            'Contenu' : 'Contenu',
            'Etat': 'Etat',
            'Note' : 'Note',
            'username': 'username',
            # 'documents' : 'documents',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le document est optionnel
        self.fields['Solution'].required = False

    def clean_Solution(self):
        file = self.cleaned_data.get('Solution')
        if file:
            max_size = 20 * 1024 * 1024  # 20 Mo
            if file.size > max_size:
                raise forms.ValidationError("Le fichier est trop grand (max 20 Mo).")

            valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpeg', '.jpg']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Extensions autorisées : {', '.join(valid_extensions)}"
                )
        return file


# Formulaire Apprenant




    def clean(self):
        """
        Validation générale du formulaire.
        Peut servir à des règles transversales.
        """
        cleaned_data = super().clean()
        nom = cleaned_data.get("Nom")
        prenom = cleaned_data.get("Prenom")

        if nom and prenom:
            # Exemple de validation supplémentaire : éviter les doublons exacts
            if nom.lower() == prenom.lower():
                raise ValidationError("Le nom et le prénom ne peuvent pas être identiques.")
        return cleaned_data


class GroupeTravailForm(forms.ModelForm):

    class Meta:
        model = GroupeTravails
        exclude = ['create_at','username'
                   ]
        fields = ['Groupe','Responsable','Contact','Discipline',
        'CodeAffect','logo','username']

        widgets = {
            'Groupe': forms.TextInput(attrs={'class': 'form-control'}),
            'Responsable': forms.TextInput(attrs={'class': 'form-control'}),
            'Contact': forms.TextInput(attrs={'class': 'form-control'}),
            'Discipline': forms.Select(attrs={'class': 'form-control'}),
            'CodeAffect': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

        labels = {
            'Groupe': 'Nom Groupe Travail :',
            'Responsable': 'Responsable :',
            'Contact': 'Contact :',
            'Discipline': 'Discipline :',
            'CodeAffect': 'Code Invitation:',
            'logo':'logo :',
            'username': 'Utilisateur :',
        }

class form_grpe_travails(forms.ModelForm):

    class Meta:
        model = form_grpe_travails
        exclude = ['create_at'
                   ]
        fields = ['Matricule', 'groupetravail']

        widgets = {
            'Matricule': forms.TextInput(attrs={'class': 'form-control'}),
        }

        labels = {
            'Matricule': 'Matricule :',
        }

# Document Groupe de Travail

class DossiersGRPTravForm(forms.ModelForm):
    #Discipline = forms.ModelChoiceField(
      #  queryset=Discipline.objects.all(),
      #  widget=forms.Select(attrs={'class': 'form-control'})
    #)

    class Meta:
        model = DossiersGRPTrav

        fields = ['Discipline', 'Niveau', 'Titre', 'TypeDoc',
                  'Observation', 'Etat','Document'
                  ]

        widgets = {
            'Groupe': forms.TextInput(attrs={'class': 'form-control'}),
            'Discipline': forms.Select(attrs={'class': 'form-control'}),
            'Niveau': forms.Select(attrs={'class': 'form-control'}),
            'Titre': forms.TextInput(attrs={'class': 'form-control'}),
            'TypeDoc': forms.Select(attrs={'class': 'form-control'}),
            'Etat': forms.Select(attrs={'class': 'form-control'}),
            'Observation': forms.Textarea(attrs={'rows': 4,'class': 'form-control'}),
            'Document': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpeg,.jpg',
                'onchange': 'validateFileSize(this)'
            }),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'Dossier_link': forms.URLInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'Groupe': 'Groupe',
            'Discipline': 'Discipline',
            'Niveau': 'Niveau',
            'TypeDoc': 'Type Document',
            'Etat': 'Etat',
            'Observation': 'Observation',
            'Titre': 'Titre',
            'Document': 'Document',
            'username': 'Utilisateur',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le document est optionnel
        self.fields['Document'].required = False

    def clean_Document(self):
        file = self.cleaned_data.get('Document')
        if file:
            max_size = 20 * 1024 * 1024  # 20 Mo
            if file.size > max_size:
                raise forms.ValidationError("Le fichier est trop grand (max 20 Mo).")

            valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpeg', '.jpg']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Extensions autorisées : {', '.join(valid_extensions)}"
                )
        return file
# Groupe Etude

class GroupeEtudeForm(forms.ModelForm):

    class Meta:
        model = GroupeEtude
        exclude = ['create_at','username'
                   ]
        fields = ['Groupe','Responsable','Contact','Etablissement','Niveau',
        'CodeAffect','logo','username']

        widgets = {
            'Groupe': forms.TextInput(attrs={'class': 'form-control'}),
            'Responsable': forms.TextInput(attrs={'class': 'form-control'}),
            'Contact': forms.TextInput(attrs={'class': 'form-control'}),
            'Niveau': forms.Select(attrs={'class': 'form-control'}),
            'Etablissement': forms.TextInput(attrs={'class': 'form-control'}),
            'CodeAffect': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),

        }

        labels = {
            'Groupe': 'Nom Groupe Etude :',
            'Responsable': 'Responsable :',
            'Contact': 'Contact :',
            'Niveau': 'Niveau',
            'Etablissement': 'Etablissement :',
            'CodeAffect': 'Code Invitation:',
            'logo':'logo :',
            'username': 'Utilisateur :',
        }

class DossiersGRPEtudeForm(forms.ModelForm):

    class Meta:
        model = DossiersGRPEtude
        exclude = ['create_at','username',     ]
        fields = ['Discipline', 'Niveau', 'Titre', 'TypeDoc',
                  'Observation', 'Etat','Document','username'
                  ]

        widgets = {
            'Groupe': forms.TextInput(attrs={'class': 'form-control'}),
            'Discipline': forms.Select(attrs={'class': 'form-control'}),
            'Niveau': forms.Select(attrs={'class': 'form-control'}),
            'Titre': forms.TextInput(attrs={'class': 'form-control'}),
            'TypeDoc': forms.Select(attrs={'class': 'form-control'}),
            'Etat': forms.Select(attrs={'class': 'form-control'}),
            'Observation': forms.Textarea(attrs={'rows': 4,'class': 'form-control'}),
            'Document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'Dossier_link': forms.URLInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'Groupe': 'Groupe',
            'Discipline': 'Discipline',
            'Niveau': 'Niveau',
            'TypeDoc': 'Type Document',
            'Etat': 'Etat',
            'Observation': 'Observation',
            'Titre': 'Titre',
            'Document': 'Document',
            'username': 'Utilisateur',
        }

        def __init__(self, *args, **kwargs):
            super(self).__init__(*args, **kwargs)
            # Pour ne pas remplacer accidentellement un fichier existant
            self.fields['Document'].required = False



def chemin_upload():
    return None

# Forum
class SujetForm(forms.ModelForm):
    class Meta:
        model = SujetDiscussion
        fields = ['titre']

class MessageForm(forms.ModelForm):
    class Meta:
        model = MessageDiscussion
        fields = ['contenu']
        widgets = {
            'contenu': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {

            'contenu': 'contenu',

        }


# Meeting
class ReunionForm(forms.ModelForm):
    # apprenants = forms.ModelMultipleChoiceField(
    #     queryset=CustomUser.objects.filter(role='apprenant'),
    #     widget=forms.CheckboxSelectMultiple,
    #     label="Apprenants participants"
    # )
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['maclasse'].queryset = MaClasse.objects.filter(username=user)


    class Meta:
        model = Reunion
        exclude = ['apprenants']
        fields = ['maclasse','titre', 'description', 'date_debut', 'date_fin','meet_link','etat','apprenants']
        widgets = {
            'maclasse': forms.Select(attrs={'class': 'form-control'}),
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'date_debut': forms.DateTimeInput(attrs={'type': 'date:"d-m-y\\TH:i"', 'class': 'form-control'}),
            'date_fin': forms.DateTimeInput(attrs={'type': 'date:"d-m-y\\TH:i"', 'class': 'form-control'}),
            'meet_link': forms.URLInput(attrs={'class': 'form-control'}),
            'etat': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'maclasse': 'Ma Classe',
            'titre': 'Titre de la réunion',
            'description': 'Description',
            'date_debut': 'Date et heure de début',
            'date_fin': 'Date et heure de fin',
            'etat': 'Terminé',
        }

class ReunionEtudeForm(forms.ModelForm):
        # Selectionne les Groupes de l'apprenant uniquement
        def __init__(self, *args, **kwargs):
            user = kwargs.pop('user', None)
            super(ReunionEtudeForm, self).__init__(*args, **kwargs)
            if user:
                self.fields['groupeetude'].queryset = GroupeEtude.objects.filter(username=user)


        class Meta:
            model = ReunionEtude
            exclude = ['apprenants']
            fields = ['groupeetude', 'titre', 'description', 'date_debut', 'date_fin', 'meet_link', 'etat', 'apprenants']
            widgets = {
                'groupeetude': forms.Select(attrs={'class': 'form-control'}),
                'titre': forms.TextInput(attrs={'class': 'form-control'}),
                'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
                'date_debut': forms.DateTimeInput(attrs={'type': 'date:"d-m-y\\TH:i"', 'class': 'form-control'}),
                'date_fin': forms.DateTimeInput(attrs={'type': 'date:"d-m-y\\TH:i"', 'class': 'form-control'}),
                'meet_link': forms.URLInput(attrs={'class': 'form-control'}),
                'etat' : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            }
            labels = {
                'groupeetude': 'Groupe Etude',
                'titre': 'Titre de la réunion',
                'description': 'Description',
                'date_debut': 'Date et heure de début',
                'date_fin': 'Date et heure de fin',
                'meet_link': 'Lien Meeting',
                'etat': 'Terminé ===',
            }


class ReunionGrpTravailForm(forms.ModelForm):
    # Selectionne les Groupes du formateur uniquement
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ReunionGrpTravailForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['groupetravail'].queryset = GroupeTravails.objects.filter(username_id=user)


    class Meta:
        model = ReunionGrpTravail
        exclude = ['formateurs']
        fields = ['groupetravail', 'titre', 'description', 'date_debut', 'date_fin', 'meet_link', 'etat', 'formateurs']
        widgets = {
            'groupetravail': forms.Select(attrs={'class': 'form-control'}),
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'date_debut': forms.DateTimeInput(attrs={'type': 'date:"d-m-y\\TH:i"', 'class': 'form-control'}),
            'date_fin': forms.DateTimeInput(attrs={'type': 'date:"d-m-y\\TH:i"', 'class': 'form-control'}),
            'meet_link': forms.URLInput(attrs={'class': 'form-control'}),
            'etat': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'groupetravail': 'Groupe Travail',
            'titre': 'Titre de la réunion',
            'description': 'Description',
            'date_debut': 'Date et heure de début',
            'date_fin': 'Date et heure de fin',
            'etat': 'Terminé ===',
        }


class PubliciteForm(forms.ModelForm):
    class Meta:
        model = Publicite
        fields = ['titre','image','lien','actif']
        help_texts = {
            'image': 'Selectionnez votre affiche publicitaire',
        }

        widgets = {

            'titre': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Ex : Entrez un titre clair et court.'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control','placeholder': 'Ex : Selection votre affiche.'}),
            'lien': forms.URLInput(attrs={'class': 'form-control','placeholder': 'Ex : http://...'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'titre': 'Titre de la publicité',
            'description': 'Description',
            'lien': 'Lien vers votre site web',
            'actif': 'actif',
        }



class CoursAdomForm(forms.ModelForm):
    class Meta:
        model = CoursAdomicile
        fields = ['titre','Discipline','image','description','actif']

        widgets = {

            'titre': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Ex : Entrez un titre clair et court.'}),
            'Discipline': forms.Select(attrs={'class': 'form-control','placeholder': 'Ex : Selectionnez votre disciplinaire.'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control','placeholder': 'Ex : Entrez un text clair et court.'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }
        labels = {

            'titre': 'Titre',
            'image': 'Prospectus',
            'description': 'Description',
            'actif': 'Actif[ ] ',


        }


class CentreFormationForm(forms.ModelForm):
    class Meta:
        model = CentreFormation

        fields = ['NomEtablissement','description','Logo','lien','actif']
        widgets = {

            'NomEtablissement': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Ex : Entrez le Nom de l\'ETS'}),
            'Logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control','placeholder': 'Ex : Entrez un text clair et court.'}),
            'lien': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ex : http://...'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }

        labels = {

            'NomEtablissement': 'Nom Etablissement',
            'Logo': 'Logo',
            'description': 'Description',
            'lien':'lien',
            'actif': 'Actif[ ] ',


        }


class ActivationForm(forms.ModelForm):

    class Meta:
        model = Activation

        fields = ['Matricule','CodeActivation','Delais','Etat']
        widgets = {

            'Matricule': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Ex : Entrez un matricule'}),
            # 'CodeActivation': forms.CharField(),
            # 'Delais': forms.IntegerField(),
            'Etat': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }

        labels = {
            'Matricule': 'Matricule',
            'CodeActivation': 'Code Activation',
            'Delais': 'Delais',
            'Etat': 'Etat',

        }