import random
import uuid
from django.contrib.sites.shortcuts import get_current_site
from django.core.serializers import json
from django.http import JsonResponse, HttpResponseForbidden, JsonResponse

from django.contrib.admin.views.decorators import staff_member_required
import logging
from django.template.loader import render_to_string
from django.core.mail import send_mail,EmailMessage
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, Model
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .context_processors import global_variable
from .forms import *
# from .forms import SujetForm, MessageForm
from .models import *
from datetime import datetime
from django.db.models import Sum
# from django.contrib.auth import *
from .models import SujetDiscussion
from .models import ActivationToken
from django.urls import reverse
from .models import Visitor
User = get_user_model()
logger = logging.getLogger(__name__)
# Create your views here.
import decimal
import json
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.test import Client

# Ex: prix par Go -> tu peux stocker en settings ou DB
PRICE_PER_GB = decimal.Decimal("1000")  # FCFA ou autre


# API mobile (exposer infos + déclencher demande)
@login_required
def api_stockage_info(request):
    profile = getattr(request.user, "profil", None)
    quota = getattr(profile, "quota", 0)
    utilise = getattr(profile, "taille_utilisee", 0)
    pourcentage = round((utilise / quota) * 100, 2) if quota else 0
    return JsonResponse({
        "quota": quota,
        "utilise": utilise,
        "pourcentage": pourcentage,
    })

@csrf_exempt
@require_http_methods(["POST"])
def api_demande_quota(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth required"}, status=401)
    data = json.loads(request.body.decode("utf-8"))
    capacite = int(data.get("capacite", 0))
    want_pay = data.get("pay", False)
    price = PRICE_PER_GB * decimal.Decimal(capacite)

    qr = QuotaRequest.objects.create(user=request.user, requested_gb=capacite, price=price)
    if want_pay:
        qr.payment_status = QuotaRequest.PAYMENT_PENDING
        qr.status = QuotaRequest.STATUS_WAITING_PAYMENT
        qr.save()
        # Create payment session and return payment_url
        payment_url = "/payment/start/%d/" % qr.id
        return JsonResponse({"ok": True, "payment_url": payment_url, "request_id": qr.id})
    return JsonResponse({"ok": True, "request_id": qr.id})


# Vérifier si l'utilisateur est admin
def is_admin(user):
    return user.is_staff or user.is_superuser


# ================================
# 1️⃣ Liste des demandes
# ================================
@login_required
@user_passes_test(is_admin)
def quota_requests_list(request):
    demandes = QuotaRequest.objects.all().order_by("-date")
    return render(request, "Admin/quota_requests.html", {"demandes": demandes})


# ================================
# 2️⃣ Traiter une demande (Vue détaillée)
# ================================
@login_required
@user_passes_test(is_admin)
def process_quota_request(request, pk):
    demande = get_object_or_404(QuotaRequest, id=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        # Validation
        if action == "approve":
            demande.status = "APPROVED"
            demande.save()
            messages.success(request, "Demande approuvée. L’utilisateur doit payer maintenant.")
            return redirect("quota_requests_list")

        # Marquer comme payé
        elif action == "mark_paid"  :
             demande.status = "PAID"
             demande.save()
             # Mise à jour effective du quota utilisateur
             user_quota = Formateurs.objects.get(username_id=demande.user.id)
             user_quota.QuotaDossier += (demande.requested_gb* 1024 * 1024 * 1024)
             user_quota.save()
             messages.success(request, "Paiement confirmé et quota mis à jour !")
             return redirect("quota_requests_list")

        # Rejet
        elif action == "reject":
            demande.status = "REJECTED"
            demande.save()
            messages.error(request, "Demande rejetée.")
            return redirect("quota_requests_list")

    return render(request, "admin/process_quota_request.html", {"demande": demande})


# ================================
# 3️⃣ Vue pour simuler un paiement
# ================================
@login_required
def fake_payment(request, pk):
    nom_session = request.session.get('compte', 'Inconnu')
    base_template = ""

    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        # Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        # Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
    demande = get_object_or_404(QuotaRequest, id=pk)

    if request.method == "POST":
        return redirect("process_quota_request", pk=demande.id)

    return render(request, "fake_payment.html", {"demande": demande,'base_template': base_template})
@login_required

def fake_payment_simulator(request, request_id):
    nom_session = request.session.get('compte', 'Inconnu')
    base_template = ""

    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        # Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        # Types = get_object_or_404(Apprenants, username_id=request.user.id).Type

    qr = get_object_or_404(QuotaRequest, id=request_id, user=request.user)
    if request.method == "POST":
        # Simuler un provider appelant notre webhook
        # Créons une payload et appelons localement la vue webhook
        payload = {
            "qr_id": qr.id,
            "reference": f"SIM-{qr.id}",
            "status": "SUCCESS",
            "amount": str(qr.price)
        }
        # Option: utiliser requests.post vers /payment/webhook/ si exposé
        c = Client()
        resp = c.post(reverse("payment_webhook"), data=json.dumps(payload), content_type="application/json")
        return redirect("payment_webhook")
    return render(request, "fake_payment.html", {"qr": qr,'base_template': base_template})

@login_required
def demande_quota(request):
    if request.method == "POST":
        capacite = int(request.POST.get("capacite", 0))
        action = request.POST.get("action", "request")  # "request" ou "pay"
        price = PRICE_PER_GB * decimal.Decimal(capacite)

        qr = QuotaRequest.objects.create(
            user=request.user,
            requested_gb=capacite,
            price=price,
            payment_status=QuotaRequest.PAYMENT_NONE,
            status=QuotaRequest.STATUS_NEW
        )

        if action == "pay":
            # Option B: préparer paiement -> renvoyer au front la référence / url
            qr.payment_status = QuotaRequest.PAYMENT_PENDING
            qr.status = QuotaRequest.STATUS_WAITING_PAYMENT
            qr.save()

            # Ici appeler le provider de paiement pour créer une session/payment request
            # Exemple pseudo: create_payment_session(amount=price, ref=qr.pk, user=request.user)
            # Retourne payment_url et payment_reference
            payment_url = reverse("payment_start", kwargs={"request_id": qr.id})  # frontend will call real API
            return redirect(payment_url)

        # Option A: simple demande sans paiement — admin validera
        # on garde status = new
        return redirect("stockage_page")  # redirige vers la page stockage ou message
    return HttpResponseForbidden()

@login_required
def payment_start(request, request_id):
    nom_session = request.session.get('compte', 'Inconnu')
    base_template = ""

    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        # Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        # Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
    context = {
        # "Types": Types,
        'base_template': base_template,
    }
    qr = get_object_or_404(QuotaRequest, id=request_id, user=request.user)

    # IMPORTANT: ici, tu dois implémenter l'appel réel au fournisseur de paiement.
    # Exemple (pseudocode):
    # response = provider.create_payment(amount=str(qr.price), metadata={"qr_id": qr.id}, return_url=..., callback_url=...)
    # payment_url = response["payment_url"]
    # payment_ref = response["reference"]
    #
    # Pour l'exemple on renvoie une page qui simule la redirection.
    payment_url = reverse("fake_payment_simulator", kwargs={"request_id": qr.id})
    return redirect(payment_url, context=context)

def stokage_page(request):
    nom_session = request.session.get('compte', 'Inconnu')
    base_template=""

    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        # Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        # Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
    context = {
        # "Types": Types,
        'base_template': base_template,
    }
    return render(request, "Stockage/stockage.html",context)

@staff_member_required
def admin_list_requests(request):
    nom_session = request.session.get('compte', 'Inconnu')
    base_template = ""

    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        # Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        # Types = get_object_or_404(Apprenants, username_id=request.user.id).Type

    qs = QuotaRequest.objects.all().order_by("-created_at")
    return render(request, "Admin/quota_requests.html", {"requests": qs,'base_template': base_template})

@staff_member_required
def admin_process_request(request, pk):
    nom_session = request.session.get('compte', 'Inconnu')
    base_template = ""

    if nom_session == 'Formateur':
        base_template = "Menus/Menu.html"
        # Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/Menu.html"
        # Types = get_object_or_404(Apprenants, username_id=request.user.id).Type

    qr = get_object_or_404(QuotaRequest, pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")
        note = request.POST.get("note", "")
        if action == "approve":
            qr.status = QuotaRequest.STATUS_APPROVED
            qr.admin_note = note
            qr.processed_at = timezone.now()
            qr.save()
            # form = Formateurs.objects.get(username_id=qr.user.id)

            # Optionally: auto-apply quota after successful payment + admin policy
            # Exemple : appliquer directement
            # profile = getattr(qr.user, "user_id", None)

            # if form:
            #     # augmenter le quota du profil (convertir GB -> octets)
            #     form.QuotaDossier += form.QuotaDossier + (qr.requested_gb * 1024 * 1024 * 1024)
            #     form.save()
            # Marquer comme payé
        elif action == "mark_paid":
            qr.status = "PAID"
            qr.payment_status=QuotaRequest.PAYMENT_OK
            qr.save()
            # Mise à jour effective du quota utilisateur
            user_quota = Formateurs.objects.get(username_id=qr.user.id)
            user_quota.QuotaDossier += (qr.requested_gb * 1024 * 1024 * 1024)
            user_quota.save()
            messages.success(request, "Paiement confirmé et quota mis à jour !")
            return redirect("admin_list_requests")

        elif action == "reject":
            qr.status = QuotaRequest.STATUS_REJECTED
            qr.admin_note = note
            qr.processed_at = timezone.now()
            qr.save()

        return redirect("admin_list_requests")

    return render(request, "Admin/process_quota_request.html", {"qr": qr,'base_template': base_template})

@csrf_exempt
def payment_webhook(request):
    # Parse JSON payload from provider
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "invalid payload"}, status=400)

    # Exemple: provider envoie {"reference": "...", "status":"SUCCESS", "amount": "..."}
    reference = payload.get("reference") or payload.get("payment_reference")
    status = payload.get("status")
    # If provider passed our qr_id in metadata:
    qr_id = payload.get("metadata", {}).get("qr_id") or payload.get("qr_id")

    # Try to match either by reference or metadata
    qr = None
    if qr_id:
        try:
            qr = QuotaRequest.objects.get(id=int(qr_id))
        except QuotaRequest.DoesNotExist:
            qr = None
    if not qr and reference:
        qr = QuotaRequest.objects.filter(payment_reference=reference).first()

    if not qr:
        return JsonResponse({"error": "request not found"}, status=404)

    # Provider-specific mapping
    if status in ("SUCCESS", "COMPLETED", "PAID"):
        qr.payment_status = QuotaRequest.PAYMENT_OK
        qr.status = QuotaRequest.STATUS_PAID
        qr.payment_reference = reference or qr.payment_reference
        qr.processed_at = timezone.now()
        qr.save()
        # Ajout des capacités
        form=Formateurs.objects.get(username_id=qr.user.id)

        # Optionally: auto-apply quota after successful payment + admin policy
        # Exemple : appliquer directement
        # profile = getattr(qr.user, "user_id", None)

        if form:
            # augmenter le quota du profil (convertir GB -> octets)
            form.QuotaDossier += form.QuotaDossier + (qr.requested_gb * 1024 * 1024 * 1024)
            form.save()
        return JsonResponse({"ok": True})

    else:
        qr.payment_status = QuotaRequest.PAYMENT_FAILED
        qr.save()
        return JsonResponse({"ok": False, "status": status})

def confirmation_inscription(request, token):
    activation = get_object_or_404(ActivationToken, token=token)

    if activation.is_expired():
        message = "Le lien de confirmation a expiré."
    else:
        user = activation.user
        user.is_active = True
        user.save()
        activation.delete()  # supprimer le token après usage
        message = "Votre compte a été confirmé avec succès !"

    return render(request, 'registration/confirmation_inscription.html', {'message': message})


def home(request):
    # total_visiteurs = Visitor.visiteurs_uniques_expiration(24)  # visiteurs des dernières 24h

    #"Rechercher un utilisateur."
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
    # if Forma:
    #     # request.session['TotalFormateurs'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    #     TotalFormateur = Formateurs.objects.all().count()
    #     request.session['TotalForm']  = request.session.get('TotalForm', 0)
    #     request.session['TotalForm'] =TotalFormateur
    # if Appren:
    #     # request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    #     TotalApprenant=Apprenants.objects.all().count()
    #     request.session['TotalAppren'] = request.session.get('TotalAppren', 0)
    #     request.session['TotalAppren']=TotalApprenant

    # request.session['codeauto'] = request.session.get('codeauto', request.POST['CodeAutorisation'])
    TotalClass=MaClasse.objects.all().count()
    TotalGrpTrav=GroupeTravails.objects.all().count()
    TotalGrpEtud=GroupeEtude.objects.all().count()
    TotalInviteApp = apprenant_maclasses.objects.all().count()
    Totalpartenariat=PartenariatClasse.objects.all().count()
    TotalDocument = MesDocuments.objects.all().count()
    TotalExo=MesDossiers.objects.all().count()
    TotalForum=SujetDiscussion.objects.all().count()
    TotalCours = CoursAdomicile.objects.all().count()
    # TotalFormateur = Formateurs.objects.all().count()
    # TotalApprenant=Apprenants.objects.all().count()
    # request.session['TotalApprenant'] = TotalApprenant
    # request.session['TotalFormateur'] = TotalFormateur
    Disc=Discipline.objects.all()
    TypeDocs = TypeDocument.objects.all()
    "Votre publicité"
    pubs = Publicite.objects.filter(actif=True)
    cours = CoursAdomicile.objects.filter(actif=True)
    if not (Appren or Forma):  # non existant
        context = {
            # "Types": nom_session,
            'TotalClass': TotalClass,
            'TotalGrpTrav': TotalGrpTrav,
            'TotalGrpEtud': TotalGrpEtud,
            'TotalInviteApp': TotalInviteApp,
            'TotalDocument': TotalDocument,
            'Totalpartenariat': Totalpartenariat,
            'TotalExo': TotalExo,
            'TotalForum': TotalForum,
            'pubs': pubs,
            'cours': cours,
            'Disc': Disc,
            'TotalCours': TotalCours,
            # 'TotalApprenant': request.session['TotalAppren'],
            'TypeDocs':TypeDocs,


        }
        return render(request, 'index.html',context=context)
    else:  # si existant
        if Forma:
            # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
            # nom_session = request.session.get('compte', 'Inconnu')
            context = {
                'MesClas': MaClasse.objects.filter(username_id=request.user.id),
                # "Types": nom_session,
                'TotalClass' : TotalClass,
                'TotalGrpTrav' :TotalGrpTrav,
                'TotalGrpEtud' : TotalGrpEtud,
                'TotalInviteApp': TotalInviteApp,
                'TotalDocument': TotalDocument,
                'Totalpartenariat': Totalpartenariat,
                'TotalExo': TotalExo,
                'TotalForum': TotalForum,
                'pubs': pubs,
                'cours': cours,
                'Disc': Disc,
                'TotalCours': TotalCours,
                # 'TotalApprenant': request.session['TotalAppren'],
                'TypeDocs': TypeDocs,

            }
            return render(request, 'index.html', context)

        if Appren:
            # request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                # "Types": nom_session,
                'TotalClass': TotalClass,
                'TotalGrpTrav': TotalGrpTrav,
                'TotalGrpEtud': TotalGrpEtud,
                'TotalDocument': TotalDocument,
                'Totalpartenariat': Totalpartenariat,
                'TotalExo': TotalExo,
                'TotalForum': TotalForum,
                'pubs': pubs,
                'cours': cours,
                'Disc': Disc,
                'TotalCours': TotalCours,
                # 'TotalApprenant': request.session['TotalAppren'],
                'TypeDocs': TypeDocs,

            }

            return render(request, 'index.html',context)

def autorisation(request):

    if request.method == 'POST':
        forma=Formateurs.objects.filter(CodeAutorisation =request.POST['CodeAutorisation']).first()
        appren = Apprenants.objects.filter(CodeAutorisation=request.POST['CodeAutorisation']).first()
        if (forma or appren):
            request.session['codeauto'] = request.session.get('codeauto', request.POST['CodeAutorisation'])

            return redirect(register)
        else:
            messages.error(request, f"Erreur !!! , le code : {request.POST['CodeAutorisation']} n'existe pas !")
    return render(request, 'registration/CodeAutorisation.html', {' messages':  messages})

def register(request):
    # verifie le code d'autorisation'
    codeautos = request.session.get('codeauto', '')  # récupère la valeur ou '' si absente

    if not codeautos or not codeautos.isdigit():
        return redirect(autorisation)

    if request.user.is_authenticated:
        return redirect('monespace')

    if request.method == 'POST':
        emails = request.POST.get("email")

        utilisateur_existe = User.objects.filter(email=emails)

        if utilisateur_existe:
            messages.error(request, f"L'adresse {emails} existe déjà !")
            return render(request, 'registration/register.html', {'form': FormulaireInscription()})

        form = FormulaireInscription(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # désactivation du compte
            user.save()
            # Générer un token unique
            # token = str(uuid.uuid4())
            # expiration = timezone.now() + timezone.timedelta(days=1)
            token = ActivationToken.objects.create(user=user, token=generated_token())

            # Construire le lien de confirmation
            activation_link = request.build_absolute_uri(
                reverse('confirmation_inscription', args=[token.token])

            )
            username = form.cleaned_data.get('username')

            # --- Email de bienvenue ---
            subject = "Bienvenue sur Face-School 🎓"
            message = (
                f"Bonjour {username},\n\n"
                "Merci de votre inscription sur Face-School.\n"
                "Veuillez confirmer votre adresse e-mail pour activer votre compte.\n\n"
                "Cordialement,\nL'équipe Face-School"
            )
            from_email = settings.EMAIL_HOST_USER
            to_list = [emails]
            send_mail(subject, message, from_email, to_list, fail_silently=False)

            # --- Email de confirmation ---
            current_site = get_current_site(request)
            email_subject = "Confirmez votre adresse e-mail - Face-School"
            message2= render_to_string('registration/email_confirmation.html', {
                'user': user,
                'activation_link': activation_link,
            })


            email_msg = EmailMessage(
                email_subject,
                message2,
                from_email,
                [emails],
            )
            email_msg.content_subtype = "html"
            email_msg.send()

            messages.success(request, (
                "Votre compte a été créé avec succès ! "
                "Un e-mail de confirmation vous a été envoyé pour activer votre compte.\n\n. "
                "Veuillez activer le compte, afin de finaliser votre inscription."
            ))
            return redirect('Profil')

        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez vérifier vos informations.")
            return render(request, 'registration/register.html', {'form': form})

    else:
        form = FormulaireInscription()
        return render(request, 'registration/register.html', {'form': form})

def logout(request):
    return render(request, 'registration/login.html', {})


def Profil(request):
    return render(request, 'registration/Profil.html', {})

@login_required
def Profilformateurs(request):
    disc= Discipline.objects.all()
    # request.session['Forma'] = "Formateurs"
    # nom_session = request.session.get('Forma', 'Inconnu')
    context = {
        'disc': disc,
        #'nom_session': nom_session,
    }
    return render(request, 'registration/ProfilFormateurs.html', context)

@login_required
def AffProfilformateurs(request):
    Form = Formateurs.objects.filter(username_id=request.user.id).exists()
    return render(request, 'registration/ProfilFormateurs.html', {'Form':Form})

@login_required
def Profilapprenant(request):
    Nivo=Niveau.objects.all()
    # request.session['Apprenant'] = "Apprenants"
    # nom_session = request.session.get('Apprenant', 'Inconnu')

    context = {
        'Nivo': Nivo,
        #'nom_session': nom_session,

    }
    return render(request, 'registration/ProfilApprenants.html', context)


def password_reset(request):
    return render(request, 'registration/password_reset.html')

@login_required
def ajouter_ProfilFormateur(request):
    # verifie le code d'autorisation'
    codeautos = request.session.get('codeauto', '')  # récupère la valeur ou '' si absente

    if not codeautos or not codeautos.isdigit():
        return redirect(autorisation)
    if request.method == "POST":
        # ✅ Vérification de la photo si elle est présente
        photo = request.FILES.get("photo")
        if photo:
            # Taille maximale 300 Ko
            if photo.size> 300 * 1024:
                messages.error(request, "La photo dépasse la taille maximale de 300 Ko.")
                return redirect(Profilformateurs)

        MatriculeForm = request.POST.get("MatriculeForm")
        LoginForm = request.POST.get("LoginForm")
        Email = request.POST.get("email")
        Photo = request.FILES.get("photo")  # dossier dans MEDIA
        nomForm = request.POST.get("nomForm")
        prenomForm = request.POST.get("prenomForm")
        DateNaissance = request.POST.get("DateNaissance")
        TelForm = request.POST.get("TelForm")
        discipline = request.POST.get("Disc")
        Type = request.POST.get("Type")
        Pays = request.POST.get("Pays")
        Sexe = request.POST.get("Sexe")
        Effectif = request.POST.get("Effectif")
        username_id = request.POST.get("username_id")
        if not DateNaissance:
            messages.success(request,'Veillez Saisir une date de naissance valide')
            return redirect(Profilformateurs)

        Format = Formateurs(
            Matricule=MatriculeForm,
            Login=LoginForm,
            Email=Email,
            Photo=Photo,  # dossier dans MEDIA
            Nom=nomForm,
            Prenom=prenomForm,
            DateNaissance=DateNaissance,
            Tel=TelForm,
            Discipline_id=discipline,
            Type=Type,
            Pays=Pays,
            Sexe=Sexe,
            Effectif=Effectif,
            username_id=username_id,
            CodeEnregistrement=request.session['codeauto'],

        )
        Format.save()
        form = get_object_or_404(Formateurs, username_id=request.user.id)
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        Types = request.session.get('compte')
        formateur = ProfilFormateursForm(Formateurs, instance=form)

        if ProfilFormateursForm.is_valid:
            return render(request, 'MonEspace.html', {'formateur': formateur, 'Types': Types})
        else:
            return render(request, 'registration/ProfilFormateurs.html', {Types: Types})
    return redirect(Profilformateurs)

@login_required
def ajouter_ProfilApprenant(request,*args,**kwargs):
    # verifie le code d'autorisation'
    codeautos = request.session.get('codeauto', '')  # récupère la valeur ou '' si absente

    if not codeautos or not codeautos.isdigit():
        return redirect(autorisation)

    if request.method == 'POST':
        Verifmatricule=Apprenants.objects.filter(Matricule=request.POST.get("MatriculeAp")).first()
        if Verifmatricule:
            messages.success(request, f'Désolé !!!,Ce Matricule:{request.POST.get("MatriculeAp")} existe !!!')
            Types = request.session.get('compte')

           #return render(request, 'registration/ProfilApprenants.html', {Types: Types})
            return redirect(Profilapprenant)

        Appren = Apprenants(
            Matricule=request.POST.get("MatriculeAp"),
            Login=request.POST.get("LoginAp"),
            Email=request.POST.get("email"),
            Nom=request.POST.get("nomAp"),
            Prenom=request.POST.get("prenomAp"),
            DateNaissance=request.POST.get("DateNaissance"),
            Tel=request.POST.get("TelAp"),
            Niveau=request.POST.get("Niveau"),
            CodeEts=request.POST.get("CodeEts"),
            Type=request.POST.get("Type"),
            Pays=request.POST.get("Pays"),
            Sexe=request.POST.get("Sexe"),
            Effectif=request.POST.get("Effectif"),
            username_id=request.POST.get("username_id"),
            DateDuJour=timezone.now(),
            Photo=request.FILES.get("photo"),  # dossier dans MEDIA
            CodeEnregistrement=request.session['codeauto'],
        )
        Appren.save()
    Appren = get_object_or_404(Apprenants, username_id=request.user.id)
    Apprenant = ProfilFormateursForm(instance=Appren)
    request.session['compte'] = Appren.Type
    # Types = request.session.get('compte')
    if ProfilApprenantForm.is_valid:
        return render(request, 'MonEspaceAp.html', {'Apprenant': Apprenant})
    else:
        return render(request, 'registration/ProfilApprenants.html', )


def AffProfil(request, pk):  # Pour afficher les Profils simplements
    if request.session['compte'] == "Apprenant":
        #Appren = get_object_or_404(Apprenants, username_id =pk)
        Appren = Apprenants.objects.get(username_id=pk)
        request.session['compte'] = Apprenants.objects.get(username_id=pk).Type
        nom_session = request.session.get('compte')
        photo=Apprenants.objects.get(username_id=pk).Photo

        apprenant = ProfilApprenantForm(instance=Appren)
        context = {'apprenant': apprenant,
                   'Appren': Appren,
                   # 'Types': nom_session,
                   'photo': photo,
                   }
        if Appren:
            return render(request, 'registration/AffProfilApprenant.html', context)

    if request.session['compte'] == "Formateur":
        #forma = get_object_or_404(Formateurs, username_id =pk)
        forma = Formateurs.objects.get(username_id=pk)
        request.session['compte'] = Formateurs.objects.get(username_id=pk).Type
        photo=Formateurs.objects.get(username_id=pk).Photo
        nom_session = request.session.get('compte')
        formateur = ProfilFormateursForm(instance=forma)
        context = {'formateur': formateur,
                   'forma': forma,
                   # 'Types': nom_session,
                   'photo': photo,
                   }
        if forma:
            return render(request, 'registration/AffProfilFormateur.html', context)


def ProfilModifier(request, pk):  # Pour modifier les Profiles
    if request.session['compte'] == "Apprenant":
        Apprens = Apprenants.objects.get(username_id=pk)
        Appren=Apprenants.objects.get(Matricule=Apprens.Matricule)
        form = ProfilApprenantForm(instance=Appren)
        # request.session['compte'] = Apprenants.objects.get(username_id=pk).Type
        # nom_session = request.session.get('compte')

        context = {'form': form,
                   'Appren': Appren,
                   # 'Types': nom_session,
                   'pk': pk,
                   }
        return render(request, 'registration/ProfilApprenant.html', context)

    if request.session['compte'] == "Formateur":
        #forma = get_object_or_404(Formateurs, username_id =pk)
        formas = Formateurs.objects.get(username_id=pk)
        forma = Formateurs.objects.get(Matricule=formas.Matricule)
        form = ProfilFormateursForm(instance=forma)
        request.session['compte'] = Formateurs.objects.get(username_id=pk).Type
        nom_session = request.session.get('compte')

        context = {'form': form,
                   'forma': forma,
                   'Types': nom_session,
                   'pk': pk,
                   }

        return render(request, 'registration/ProfilFormateur.html', context)

def update_ProfilApprenant(request, pk):
    # Vérifie si l’utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour modifier votre profil.")
        return redirect('login')

    # Récupère l’apprenant lié à l’utilisateur connecté
    apprenant = get_object_or_404(Apprenants, username_id=pk)

    # Liste des niveaux à afficher dans la liste déroulante
    niveaux = Niveau.objects.all()

    if request.method == "POST":
        form = ProfilApprenantForm(request.POST, request.FILES, instance=apprenant)

        if form.is_valid():

            # Vérification de la photo
            photo = request.FILES.get("photo")
            if photo:
                # Limite de taille (300 Ko)
                if photo.size > 300 * 1024:
                    messages.error(request, "La photo dépasse la taille maximale de 300 Ko.")
                    return render(request, "registration/ProfilApprenant.html", {
                        "Appren": apprenant,
                        "Nivo": niveaux,
                        "form": form,
                    })
                # Vérification de l’extension
                valid_extensions = ['.jpg', '.jpeg', '.png']
                import os
                ext = os.path.splitext(photo.name)[1].lower()
                if ext not in valid_extensions:
                    messages.error(request, "Format de fichier non autorisé. Utilisez JPG ou PNG.")
                    return render(request, "registration/ProfilApprenant.html", {
                        "Appren": apprenant,
                        "Nivo": niveaux,
                        "form": form,
                    })

            # Enregistrement du formulaire
            form.save()
            messages.success(request, "Profil mis à jour avec succès ✅")
            return redirect("ProfilModifier", pk=pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = ProfilApprenantForm(instance=apprenant)

    context = {
        "Appren": apprenant,
        "form": form,
        "Nivo": niveaux,
    }
    return render(request, "registration/ProfilApprenant.html", context)


def update_ProfilFormateur(request, pk):
    # Vérifie que l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour modifier votre profil.")
        return redirect('login')

    # Récupère le formateur correspondant
    forma = get_object_or_404(Formateurs, username_id=request.user.id)
    niveaux = Niveau.objects.all()  # Liste déroulante des niveaux

    if request.method == "POST":
        form = ProfilFormateursForm(request.POST, request.FILES, instance=forma)

        if form.is_valid():

            Photo = request.FILES.get("Photo")

            # ✅ Vérification de la photo si elle est présente
            if Photo:

                # Taille maximale 300 Ko
                if Photo.size > 300 * 1024:
                    messages.error(request, "La photo dépasse la taille maximale de 300 Ko.")
                    return render(request, "registration/ProfilFormateur.html", {
                        "forma": forma, "Nivo": niveaux, "form": form,
                    })

                # Vérifie l'extension du fichier
                valid_extensions = ['.jpg', '.jpeg', '.png']
                ext = os.path.splitext(Photo.name)[1].lower()
                if ext not in valid_extensions:
                    messages.error(request, "Format de fichier non autorisé. Utilisez JPG ou PNG.")
                    return render(request, "registration/ProfilFormateur.html", {
                        "forma": forma, "Nivo": niveaux, "form": form,
                    })

            # ✅ Sauvegarde finale
            form.save()
            messages.success(request, "Profil mis à jour avec succès ✅")
            return redirect("ProfilModifier", pk=pk)

        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = ProfilFormateursForm(instance=forma)

    # ✅ Contexte pour l'affichage
    context = {
        "forma": forma,
        "Nivo": niveaux,
        "form": form,
    }

    return render(request, "registration/ProfilFormateur.html", context)
    # # =================================================================================
    #
    # forma = Formateurs.objects.get(username_id=pk)
    # formateur = ProfilFormateursForm(request.POST, request.FILES, instance=forma)
    #
    # # Format = Formateurs.objects.filter(username_id=code).exists()
    # Types = request.session.get('compte')
    # context = {'formateur': formateur,
    #            'forma': forma,
    #            'Types': Types,
    #            }
    # formateur.save()
    # return render(request, 'registration/AffProfilFormateur.html', context)
    # # else:
    # #return render(request, 'registration/ProfilFormateurs.html', context)


def presentation(request):


    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if not (Appren or Forma):  # non existant
        return render(request, 'Presentation.html')
    else:  # si existant
        if Forma:
            request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                'MesClas': MaClasse.objects.filter(username_id=request.user.id),
                "Types": nom_session,

            }
            return render(request, 'Presentation.html',context)

        if Appren:
            request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                "Types": nom_session,

            }

    return render(request, 'Presentation.html',context)


def services(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if not (Appren or Forma):  # non existant
        return render(request, 'index.html', {})
    else:  # si existant
        if Forma:
            request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                "Types": nom_session,
            }
            return render(request, 'Services.html',context)

        if Appren:
            request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                "Types": nom_session,
            }

    return render(request, 'Services.html',context)


def contacts(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if not (Appren or Forma):  # non existant
        return render(request, 'Contacts.html')
    else:  # si existant
        if Forma:
            request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                    "Types": nom_session,
            }
            return render(request, 'Contacts.html',context)

        if Appren:
            request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            context = {
                "Types": nom_session,
            }
    return render(request, 'Contacts.html',context)

@login_required
def formateurs(request):
    if request.user.is_authenticated:  # connecte

        # if  request.session['compte']=="Formateur":
        #request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id)
        nom_session = request.session.get('compte')
        context = {
            "Types": nom_session,
        }
        #else:
        #request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        #   nom_session = request.session.get('compte')
        #  context = {
        #     "Types": nom_session,
        #}
        return render(request, 'Formateurs.html', context)
    else:  # non connecte
        return render(request, 'Formateurs.html')

@login_required
def apprenant(request):
    if request.user.is_authenticated:  # connecte
        #if request.session['compte'] == "Apprenant":
        #request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte')
        context = {
            "Types": nom_session,
        }

        return render(request, 'Apprenants.html', context)
    else:
        return render(request, 'Apprenants.html')

@login_required
def MesClasses(request):
    Types=request.session.get('compte')
    if Types=='Formateur':
        MesClas= MaClasse.objects.filter(username_id=request.user.id).order_by('id')
        paginator = Paginator(MesClas, 10)  # 10 réunions par page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {
            'MesClas': page_obj,
            'TotalClasse': MaClasse.objects.filter(username_id=request.user.id).count(),
            "Types": Types
        }
        return render(request, 'LesClasses/MesClasses.html', context)

    if Types == 'Apprenant':
        Appren= Apprenants.objects.filter(username_id=request.user.id).first()
        #Mesclasses= apprenant_maclasses.objects.filter(apprenant=Appren.Matricule)
        MesClas = apprenant_maclasses.objects.filter(apprenant_id=Appren.Matricule)
        paginator = Paginator(MesClas, 10)  # 10 réunions par page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        TotalClasse=apprenant_maclasses.objects.filter(apprenant_id=Appren.Matricule).count()
        #print( MesClas.values())
        context = {
            'MesClas': page_obj,
            "Types": Types,
            'TotalClasse':TotalClasse,
        }
        return render(request, 'LesClasses/MesClassesApp.html', context)

@login_required
def LesClasses(request):
    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type
    }
    return render(request, 'Classes.html', context)

def infoApprenant(request):
    nom_session = request.session.get('compte', 'Inconnu')
    Appren=Apprenants.objects.filter().order_by('-create_at')[:50]
    ApprenTotal = Apprenants.objects.filter().count()
    if nom_session == 'Formateur':
        Types=nom_session

    if nom_session == 'Apprenant':
         Types=nom_session
    else:
         Types=nom_session
    context = {
        'Types': nom_session,
        'MesClasTotal': ApprenTotal,
    }
    return render(request, 'InfoApprenants.html',context)

def infoFormateur(request):
    nom_session = request.session.get('compte', 'Inconnu')
    Form=Formateurs.objects.filter().order_by('-create_at')[:50]
    formTotal = Formateurs.objects.filter().count()
    if nom_session == 'Formateur':
        Types=nom_session

    if nom_session == 'Apprenant':
         Types=nom_session
    else:
         Types=nom_session
    context = {
        'Types': nom_session,
        'formTotal': formTotal,
    }
    return render(request, 'InfoFormateurs.html',context)

def infogroupeTravail(request):
    nom_session = request.session.get('compte', 'Inconnu')
    Form=Formateurs.objects.filter().order_by('-create_at')[:50]
    formTotal = Formateurs.objects.filter().count()
    if nom_session == 'Formateur':
        Types=nom_session

    if nom_session == 'Apprenant':
         Types=nom_session
    else:
         Types=nom_session
    context = {
        'Types': nom_session,
        'formTotal': formTotal,
    }
    return render(request, 'InfoGroupeTravail.html',context)


def infogroupetude(request):
    nom_session = request.session.get('compte', 'Inconnu')
    Form=Formateurs.objects.filter().order_by('-create_at')[:50]
    formTotal = Formateurs.objects.filter().count()
    if nom_session == 'Formateur':
        Types=nom_session

    if nom_session == 'Apprenant':
         Types=nom_session
    else:
         Types=nom_session
    context = {
        'Types': nom_session,
        'formTotal': formTotal,
    }
    return render(request, 'InfoGroupeEtude.html',context)


def infoClasses(request):
    nom_session = request.session.get('compte', 'Inconnu')
    MesClas=MaClasse.objects.filter().order_by('-create_at')[:50]
    MesClasTotal = MaClasse.objects.filter().count()
    if nom_session == 'Formateur':
        Types=nom_session

    if nom_session == 'Apprenant':
         Types=nom_session
    else:
         Types=nom_session
    context = {
        'Types': nom_session,
        'MesClas': MesClas,
        'MesClasTotal': MesClasTotal,
    }
    return render(request, 'LesClasses/InfoClasses.html',context)
@login_required
def AjouterClasses(request):
    Lniveau = Niveau.objects.all()  # Tous les Niveaux
    CodeAff = MaClasse.objects.filter(CodeAffect=request.POST.get("CodeAffect"))
    TOTALCLASS=MaClasse.objects.filter(username_id=request.user.id).count()
    nom_session = request.session.get('compte')
    context = {
        'MesClas': MaClasse.objects.filter(username_id=request.user.id),
        "Types": nom_session,
        "Lniveau": Lniveau,
        'TotalClasse': TOTALCLASS,
    }
    if request.POST.get("NomClasse") == "" or request.POST.get("niveau") == "":
        messages.success(request, 'Veillez renseigner les champs vides')
        return render(request, 'LesClasses/CreerClasses.html', context)

    if not CodeAff:
        Mclasse = MaClasse(
            NomClasse=request.POST.get("NomClasse"),
            ChefClasse=request.POST.get("ChefClasse"),
            CodeAffect=request.POST.get("CodeAffect"),
            Niveau=request.POST.get("niveau"),
            CodeEts=request.POST.get("CodeEts"),
            Login=request.user.username,
            username_id=request.user.id,
        )
        Mclasse.save()
        TOTALCLASS = MaClasse.objects.filter(username_id=request.user.id).count()
        context = {
            'MesClas': MaClasse.objects.filter(username_id=request.user.id),
            "Types": nom_session,
            "Lniveau": Lniveau,
            'TotalClasse': TOTALCLASS,
        }
        return render(request, 'LesClasses/MesClasses.html', context)
    else:
        messages.success(request, f'Erreur !!! Ce Code invitation, {request.POST.get("CodeAffect")}, existe dejà !')
        return render(request, 'LesClasses/CreerClasses.html', context)

# Creer Classe
@login_required
def CreerClasses(request):
    form = ClasseForm()
    Lniveau = Niveau.objects.all()
    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'form': form,
        'Lniveau': Lniveau
    }
    return render(request, 'LesClasses/CreerClasses.html', context)

# Partenariat
@login_required
def CreerPartenariatClasses(request,pk):
    # ListePartenariats = PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id,ClassDemandeur_id=pk).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id,ClassPartenaire_id=pk).order_by('id')
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ProfDemandeur_id=request.user.id, ClassDemandeur_id=pk) |
        Q(ProfPartenaire_id=request.user.id, ClassPartenaire_id=pk)
    ).order_by('id')

    MClasse =  get_object_or_404(MaClasse, id=pk)
    request.session['idclasse'] = MClasse.pk
    NomsessionClass = request.session.get('idclasse', 'Inconnu')
    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'pk': pk,
        'MClasse': MClasse,
        'NomsessionClass':NomsessionClass,
        'ListePartenariats': ListePartenariats,

    }

    if request.method == 'POST':
        #Eviter les auto-parrainages
        MClas = MaClasse.objects.filter(CodeAffect=request.POST.get('CodeAffect')).first()

        if not MClas:
            messages.success(request,
                             f"Le Code Classe :{request.POST.get("CodeAffect")} n'existe pas  .")
            return render(request, 'Partenariat/CreerPartClasse.html', context)

        if pk == MClas.id or  MClas.username_id == request.user.id:
            messages.success(request,
                             f"Désolé !!!,Une classe ne peut s'auto-Parrainer.")
            return render(request, 'Partenariat/CreerPartClasse.html', context)

        try:
            #form = PartenariatClasseForm(request.POST)
            #MClassesChoix = get_object_or_404(MaClasse, id= request.POST.get("IDClasse"))
            if MClasse.Niveau !=  MClas.Niveau:
                messages.success(request,
                                 f"Niveau Classe :{MClasse.Niveau} non conforme au Niveau choisir:{MClas.Niveau} .")
                return render(request, 'Partenariat/CreerPartClasse.html', context)
            # print(request.POST.get("Discipline"))

            Partenaire = PartenariatClasse(
                ClassDemandeur_id=pk,
                ProfDemandeur_id=request.user.id,
                ClassPartenaire_id=MClas.id,
                ProfPartenaire_id=MClas.username_id,
            )
            Partenaire.save()
            messages.success(request, "Partenariat crée avec Succès .")
            return redirect('CreerPartenariatClasses',pk)
            #return render(request, 'Partenariat/CreerPartClasse.html', context)
        except IntegrityError:
             messages.success(request, "Désolé !!!,Ce Partenariat existe déjà .")
    return render(request, 'Partenariat/CreerPartClasse.html', context)


#def ListepartClasse(request,pk):

  #  return render(request, 'Partenariat/ListepartClasse.html')

@login_required
def ListepartClasses(request):
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # ListePartenariats=PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id).order_by('id')

    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ProfDemandeur_id=request.user.id) | Q(ProfPartenaire_id=request.user.id)
    ).order_by('id')

    # Les Classes objets de partenariat
    MesClasPart = MaClasse.objects.filter(Q(username_id=request.user.id),
                                          Q(id__in=ListePartenariats.values_list('ClassDemandeur_id', flat=True)) |
                                          Q(id__in=ListePartenariats.values_list('ClassPartenaire_id', flat=True)))

    # ListePartenariats = PartenariatClasse.objects.filter(
    #     Q(ProfDemandeur_id=request.user.id) | Q(ProfPartenaire_id=request.user.id)
    # ).order_by('id')

    ListeClasse=MaClasse.objects.all()
    MesClasses=MaClasse.objects.filter(username_id=request.user.id)
    MesTypes = TypeDocument.objects.all()
    context={
        'ListePartenariats': ListePartenariats,
        'ListeClasse':ListeClasse,
        'MesTypes': MesTypes,
        'MesClasses': MesClasses,
        "Types": nom_session,
        'MesClasPart': MesClasPart,

    }
    return render(request,'Partenariat/ListePartClasse.html',context)

@login_required
def ListepartClassesApp(request):
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # ListePartenariats=PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id).order_by('id')
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()
    Mesclass = apprenant_maclasses.objects.filter(apprenant_id=Appren.Matricule)

    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ClassDemandeur_id__in=Mesclass.values_list('id', flat=True)) |
        Q(ClassPartenaire_id__in=Mesclass.values_list('id', flat=True))
    ).order_by('id')
    ListeClasse=MaClasse.objects.all()
    MesClasses=MaClasse.objects.filter(username_id=request.user.id)
    MesTypes = TypeDocument.objects.all()
    context={
        'ListePartenariats': ListePartenariats,
        'ListeClasse':ListeClasse,
        'MesTypes': MesTypes,
        'MesClasses': MesClasses,
        "Types": nom_session,

    }
    return render(request,'Partenariat/ListePartClasseApp.html',context)


@login_required
def ListepartMaClasse(request,pk): # Liste des classes partenaires vu des apprenants
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
    # ListePartenariats=PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id).order_by('id')
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ClassDemandeur_id=pk) | Q(ClassPartenaire_id=pk)
    ).order_by('id')

    ListeClasse=MaClasse.objects.all()
    MesClasses=MaClasse.objects.filter(id=pk)
    MesClasse = MaClasse.objects.filter(id=pk).first()
    MesTypes = TypeDocument.objects.all()
    context={
        'pk':pk,
        'ListePartenariats': ListePartenariats,
        'ListeClasse':ListeClasse,
        'MesTypes': MesTypes,
        'MesClasses': MesClasses,
        "Types": nom_session,
        'MesClasse': MesClasse,
        'base_template': base_template,

    }
    return render(request,'Partenariat/ListepartMaClasse.html',context)

# Transfert Apprenant dans une Classe
@login_required
def TransferpartClasses(request):
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    MesClasses = MaClasse.objects.filter(username_id=request.user.id)
    MesTypes = TypeDocument.objects.all()
    context = {
        'MesTypes': MesTypes,
        'MesClasses': MesClasses,
        "Types": nom_session,

    }

    try:
        if request.method == 'POST':
            # Verifie le codeaffect de la classe demandeur
            MClasseDemandeur=MaClasse.objects.filter(CodeAffect=request.POST.get('CodeAffect')).first()
            if not MClasseDemandeur:
                messages.success(request, "Désolé !!!,Ce code n'existe pas.")
                return render(request, 'LesClasses/TransferClassPartClasse.html', context)

            context = {
                'MesTypes': MesTypes,
                'MesClasses': MesClasses,
                "Types": nom_session,
                'MClasseDemandeur': MClasseDemandeur,
                }
            # Recherche les apprenants de la Classe
            Appren=apprenant_maclasses.objects.filter(maclasse_id=request.POST.get('IDClasse'))
            MclasseMere=MaClasse.objects.filter(pk=request.POST.get('IDClasse')).first() # Recherche Niveau Classe
            if not Appren:
                messages.success(request, "Désolé !!!,Cette classe n'a aucun Apprenant.")
                return render(request, 'LesClasses/TransferClassPartClasse.html', context)
            # Si les niveaux diffèrent
            if MClasseDemandeur.Niveau != MclasseMere.Niveau:
                messages.success(request, "Désolé !!!,Les classes choisie n'ont pas le même Niveau.")
                return render(request, 'LesClasses/TransferClassPartClasse.html', context)
            # Parcours la Table Classe pour le transfert
            for ap in Appren:
                Demandeur=apprenant_maclasses(
                    maclasse_id = MClasseDemandeur.pk,
                    apprenant_id=ap.apprenant_id,
                )
                Demandeur.save()
                messages.success(request, "Les Apprenants ont été Transferés avec succès.")
            context = {
                'MesTypes': MesTypes,
                'MesClasses': MesClasses,
                "Types": nom_session,
                'MClasseDemandeur': MClasseDemandeur,
                'Appren': Appren,
                'Total':Appren.count(),
            }
    except IntegrityError:
        messages.success(request, "Désolé !!!,L'Elève est déjà dans la Classe .")
    return render(request,'LesClasses/TransferClassPartClasse.html',context)

#Suppression Partenariat
@login_required
def SuppPartenariat(request, pk):
    #Partenaire = PartenariatClasse.objects.get(id=pk)
    Partenaire=get_object_or_404(PartenariatClasse, id=pk)
    # ListePartenariats = PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id)
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id)
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ProfDemandeur_id=request.user.id) | Q(ProfPartenaire_id=request.user.id)
    ).order_by('id')

    #ListeClasse = MaClasse.objects.all()
    NomsessionClass = request.session.get('idclasse', 'Inconnu')
    #Mclasse = ClasseForm(instance=Mclas)
    context = {
        'pk':pk,
        'Partenaire': Partenaire,
        'ListePartenariats': ListePartenariats,
        'NomsessionClass' :NomsessionClass,
        #'ListeClasse': ListeClasse,

    }
    Partenaire.delete()
    messages.success(request, 'Partenariat supprimer avec Succès')
    return redirect('CreerPartenariatClasses',NomsessionClass)
    #return render(request, 'Partenariat/CreerPartClasse.html', context)

@login_required
def ListeDocumentPart(request,pk):
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # ListePartenariats = PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id).order_by('id')
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ProfDemandeur_id=request.user.id) | Q(ProfPartenaire_id=request.user.id)
    ).order_by('id')

    DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    MesClasses=MaClasse.objects.filter(username_id=request.user.id)
    # Classe ayant fait Objet de partenariat
    # MesClasParts= PartenariatClasse.objects.filter(
    #     Q(ClassDemandeur_id=pk) | Q(ClassPartenaire_id=pk))
    MesClasPart=MaClasse.objects.filter(Q(id=pk) )
    nomclasse = MaClasse.objects.get(id=pk).NomClasse
    MesTypes=TypeDocument.objects.all()
    context = {
        'ListePartenariats': ListePartenariats,
        'nomclasse': nomclasse,
        'DocClass':DocClass,
        'MesTypes':MesTypes,
        'pk': pk,
        "Types": nom_session,
        'MesClasses':MesClasses,
        'MesClasPart': MesClasPart,
    }
    return render(request, 'Partenariat/ListePartClasse.html', context)

def ListeDocumentPartPublic(request,type_doc):
    # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    # nom_session = request.session.get('compte', 'Inconnu')
    niveau=Niveau.objects.all()
    disciple=Discipline.objects.all()
    # DocClass = MesDocuments.objects.filter(Etat='PUBLIC')
    # if request.method == 'POST':
    #     type_doc = request.POST['Type']
    TypeDocClass = MesDocuments.objects.filter(Etat ='PUBLIC', TypeDoc=type_doc)
    request.session['type_doc'] = type_doc

    TypeDocs=TypeDocument.objects.all()
    context = {

        # 'DocClass':DocClass,
        'TypeDocs':TypeDocs,
        'disciple':disciple,
        'TypeDocClass':TypeDocClass,
        'type_doc':type_doc,
        'niveau':niveau,

    }
    return render(request, 'Documents/ListeDocPublic.html', context)

def ListeDocumentPartPublicDisc(request,type_doc,Disc):
    # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    type_doc = request.session.get('type_doc', 'Inconnu')
    niveau=Niveau.objects.all()
    disciple=Discipline.objects.all()
    niv = ""
    TypeDocClass = MesDocuments.objects.filter(Etat='PUBLIC',TypeDoc=type_doc ,Discipline_id=Disc)
    if request.method == 'POST':
        niv = request.POST['Niveau']
        TypeDocClass = MesDocuments.objects.filter(Etat ='PUBLIC',TypeDoc=type_doc ,Discipline_id=Disc,Niveau=niv )


    # TypeDocs=TypeDocument.objects.all()
    context = {

        'niveau':niveau,
        # 'TypeDocs':TypeDocs,
        'disciple':disciple,
        'TypeDocClass':TypeDocClass,
        'Disc':Disc,
        'niv':niv,
        'type_doc':type_doc,

    }
    return render(request, 'Documents/ListeDocPublicDisc.html', context)

def ListeDocParMatierePublic(request,Matiere):
    # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    # nom_session = request.session.get('compte', 'Inconnu')
    niveau=Niveau.objects.all()
    disciple=Discipline.objects.all()
    # DocClass = MesDocuments.objects.filter(Etat='PUBLIC')
    # if request.method == 'POST':
    #     type_doc = request.POST['Type']
    MatiereDocClass = MesDocuments.objects.filter(Etat ='PUBLIC', Discipline_id =Matiere)
    request.session['Matiere'] = Matiere
    Matiere = request.session.get('Matiere', 'Inconnu')
    TypeDocs=TypeDocument.objects.all()
    context = {

        # 'DocClass':DocClass,
        'TypeDocs':TypeDocs,
        'disciple':disciple,
        'MatiereDocClass':MatiereDocClass,
        'niveau':niveau,
        'Matiere':Matiere,
    }
    return render(request, 'Documents/ListeDocMatierePublic.html', context)

def ListeDocMatierePartPublicDisc(request,Matiere,type_doc):
    # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    Matiere = request.session.get('Matiere', 'Inconnu')
    niveau=Niveau.objects.all()
    disciple=Discipline.objects.all()
    niv = ""
    TypeDocClass = MesDocuments.objects.filter(Etat='PUBLIC',Discipline_id=Matiere,TypeDoc=type_doc )
    if request.method == 'POST':
        niv = request.POST['Niveau']
        TypeDocClass = MesDocuments.objects.filter(Etat='PUBLIC',Discipline_id=Matiere,TypeDoc=type_doc,Niveau=niv )


    TypeDocs=TypeDocument.objects.all()
    context = {

        'niveau':niveau,
        'TypeDocs':TypeDocs,
        'disciple':disciple,
        'TypeDocClass':TypeDocClass,
        'Matiere':Matiere,
        'niv':niv,
        'type_doc':type_doc,

    }
    return render(request, 'Documents/ListeDocPublicMatiere.html', context)

@login_required
def ListeDocumentPartMaClasse(request,pk): # les documents de partenariat

    nom_session = request.session.get('compte')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
    # if request.session['compte'] == 'Apprenant':
    #     request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    #
    # if request.session['compte'] == 'Formateurs':
    #     request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ClassDemandeur_id=pk) | Q(ClassPartenaire_id=pk)
    ).order_by('id')
    DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    MesClasses=MaClasse.objects.filter(username_id=request.user.id)
    MesClasse = MaClasse.objects.filter(id=pk).first()
    nomclasse = MaClasse.objects.get(id=pk).NomClasse
    MesTypes=TypeDocument.objects.all()
    context = {
        'ListePartenariats': ListePartenariats,
        'nomclasse': nomclasse,
        'DocClass':DocClass,
        'MesTypes':MesTypes,
        'pk': pk,
        "Types": nom_session,
        'MesClasses':MesClasses,
        'MesClasse': MesClasse,
        'base_template': base_template,
    }
    return render(request, 'Partenariat/ListePartMaClasse.html', context)

@login_required
def ListeDocumentPartFil(request,pk):
    # ListePartenariats = PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id).order_by('id')
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ProfDemandeur_id=request.user.id) | Q(ProfPartenaire_id=request.user.id)
    ).order_by('id')

    if request.method == 'POST':
        type_doc=request.POST['Type']
        DocClass = MesDocuments.objects.filter(maclasse_id=pk, TypeDoc=type_doc)
    #DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    nomclasse = MaClasse.objects.get(id=pk).NomClasse
    MesTypes=TypeDocument.objects.all()
    context = {
        'ListePartenariats': ListePartenariats,
        'nomclasse': nomclasse,
        'DocClass':DocClass,
        'MesTypes':MesTypes,
        'pk':pk,
        'type_doc': type_doc,
    }

    return render(request, 'Partenariat/ListePartClasse.html', context)

def ListeDocumentPartClasseFil(request,pk):
    nom_session = request.session.get('compte', 'Inconnu')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ClassDemandeur_id=pk) | Q(ClassPartenaire_id=pk)
    ).order_by('id')

    if request.method == 'POST':
        type_doc=request.POST['Type']
        DocClass = MesDocuments.objects.filter(maclasse_id=pk, TypeDoc=type_doc)

    #DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    #DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    MesClasses = MaClasse.objects.filter(username_id=request.user.id)
    MesClasse = MaClasse.objects.filter(id=pk).first()
    nomclasse = MaClasse.objects.get(id=pk).NomClasse
    MesTypes=TypeDocument.objects.all()
    context = {
        'ListePartenariats': ListePartenariats,
        'nomclasse': nomclasse,
        'DocClass':DocClass,
        'MesClasses': MesClasses,
        'MesTypes':MesTypes,
        'pk':pk,
        'type_doc': type_doc,
        'MesClasse': MesClasse,
        "Types": nom_session,
        'base_template':base_template,

    }

    return render(request, 'Partenariat/ListePartMaClasse.html', context)

@login_required
def ModifClasses(request, pk):
    Mclas = MaClasse.objects.get(id=pk)
    Mclasse = ClasseForm(instance=Mclas)
    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'Mclasse': Mclasse,
        'Mclas': Mclas

    }
    return render(request, 'LesClasses/ModifierClasse.html', context)


#Supprimer une classe
@login_required
def SuppClasses(request, pk):
    Mclas = MaClasse.objects.get(id=pk)
    #Mclasse = ClasseForm(instance=Mclas)
    Mclas.delete()
    context = {
        'MesClas': MaClasse.objects.filter(username_id=request.user.id),
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type
    }
    return render(request, 'LesClasses/MesClasses.html', context)

@login_required
def UpdateClasses(request, pk):
    Mclas = MaClasse.objects.get(id=pk)
    nom_session = request.session.get('compte')
    Mclasse = ClasseForm(request.POST, instance=Mclas)

    if request.POST.get("NomClasse") == "" or request.POST.get("Niveau") == "":
        messages.success(request, 'Veillez renseigner les champs vides')
        return render(request, 'LesClasses/ModifierClasse.html')

    if Mclasse.is_valid():
        Mclasse.save()
        #messages.success(request, 'Modification effectuée avec succes')
        return redirect('MesClasses')
    else:
        Mclasse = ClasseForm(request.POST, instance=Mclas)
        #Mclas= MaClasse.objects.get(id=pk)
        context = {

            "Types": nom_session,
            'Mclasse': Mclasse,
            'Mclas': Mclas
        }
        messages.success(request, f'Code invitation:{Mclas.CodeAffect} déjà existant')
        return render(request, 'LesClasses/ModifierClasse.html', context)


#Formulaire Ajouter un Elève
@login_required
def AjouterApprClasses(request, pk):
    Mclasse = MaClasse.objects.get(id=pk)
    ApprenClasse = apprenant_maclasses.objects.filter(maclasse_id=pk).order_by('id')
    total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=pk).count()

    #print(ApprenClasse)
    context = {
        'MClasses': Mclasse,
        'ApprenClasse': ApprenClasse,
        'total_apprenants': total_apprenants,
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type
    }
    return render(request, 'LesClasses/AjouterApprClasse.html', context)
#Liste Classe par Apprenant

@login_required
def ListeApprClasses(request, pk):
    #reunions_list = Reunion.objects.all().order_by("-id")
    ListePartenariats = PartenariatClasse.objects.filter(
        Q(ClassDemandeur_id=pk) | Q(ClassPartenaire_id=pk)
    ).order_by('id')
    MessagesClasses = Message_Classes.objects.filter(maclasse_id=pk).order_by('-create_at')[:10]
    mesreunions = Reunion.objects.filter(maclasse_id=pk,etat=0)  # Toutes les reunions de la classe
    mesclasse = MaClasse.objects.filter(id=pk)  # Les classes ayant fait objet de reunion
    Mclasse = MaClasse.objects.get(id=pk)

    ApprenClasses = apprenant_maclasses.objects.filter(maclasse_id=pk).order_by('id')
    total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=pk).count()
    DocClass = MesDocuments.objects.filter(maclasse_id=pk).order_by('-id')[:25]

    context = {
        'pk':pk,
        'mesreunions': mesreunions,
        'ListePartenariats': ListePartenariats,
        'mesclasse': mesclasse,
        'MessagesClasses':MessagesClasses,
        'MClasses': Mclasse,
        'ApprenClasses': ApprenClasses,
        'total_apprenants': total_apprenants,
        'DocClass': DocClass,
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type
    }
    return render(request, 'LesClasses/ListeApprClasse.html', context)

@login_required
def ListeDocClasses(request, pk):

    MessagesClasses = Message_Classes.objects.filter(maclasse_id=pk).order_by('-id')[:10]
    mesreunions = Reunion.objects.filter(maclasse_id=pk,etat=0)  # Toutes les reunions de la classe
    mesclasse = MaClasse.objects.filter(id=pk)  # Les classes ayant fait objet de reunion
    Mclasse = MaClasse.objects.get(id=pk)
    DocClass = MesDocuments.objects.filter(maclasse_id=pk).order_by('-id')[:25]
    Apprens=apprenant_maclasses.objects.filter(maclasse_id=pk).order_by('id') # Les Apprenants de la classe
    Appren=Apprenants.objects.filter(Matricule__in=Apprens.values_list('apprenant_id', flat=True))

    # ListeAppren=Apprenants.objects.filter(Matricule__in=Appren.values_list('apprenant_id', flat=True)).order_by('id')
    context = {
        'pk':pk,
        'mesreunions': mesreunions,
        'mesclasse': mesclasse,
        'MessagesClasses':MessagesClasses,
        'MClasses': Mclasse,
        'DocClass': DocClass,
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        'Appren': Appren,
    }
    return render(request, 'LesClasses/ListeDocClasse.html', context)

@login_required
def SupAppClasses(request, pk):
    ApprenClas = apprenant_maclasses.objects.filter(id=pk).first()
    total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=ApprenClas.maclasse_id).count()
    Mclasse = MaClasse.objects.get(id=ApprenClas.maclasse_id)
    ApprenClasse = apprenant_maclasses.objects.filter(maclasse_id=ApprenClas.maclasse_id)
    # print(ApprenClasse)
    context = {
        'MClasses': Mclasse,
        'ApprenClasse': ApprenClasse,
        'total_apprenants': total_apprenants,
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type
    }
    ApprenClas.delete()
    return render(request, 'LesClasses/AjouterApprClasse.html', context)


# Inscrire Apprenant dans une Classe
@login_required
def InscrireApprClasses(request, pk):
    Mclasse = MaClasse.objects.get(id=pk)
    matricule = request.POST.get("Matricule")
    Appren = Apprenants.objects.filter(Matricule=matricule).first()

    ApprenClasse = apprenant_maclasses.objects.filter(maclasse_id=pk).order_by('id')
    total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=pk).count()

    context = {
        'MClasses': Mclasse,
        'ApprenClasse': ApprenClasse,
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'total_apprenants': total_apprenants,
    }
    if not Appren:
        messages.success(request, f'Matricule : {request.POST.get("Matricule")} inexistant')
        return render(request, 'LesClasses/AjouterApprClasse.html', context)

    # Quand le Niveau est different
    if Mclasse.Niveau != Appren.Niveau:
        messages.success(request, f"Cet élève : {request.POST.get("Matricule")} n'a pas le Niveau de la classe")
        return render(request, 'LesClasses/AjouterApprClasse.html', context)

    if apprenant_maclasses.objects.filter(maclasse_id=pk, apprenant_id=request.POST.get("Matricule")).exists():
        messages.success(request, f'Elève:{request.POST.get("Matricule")} déjà inscrit dans la Classe')
        return render(request, 'LesClasses/AjouterApprClasse.html', context)

    inscription = apprenant_maclasses(
        apprenant_id=matricule,
        maclasse_id=pk
    )
    inscription.save()
    total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=pk).count()
    Mclasse.Effectif=total_apprenants # Mise à jour effectif classe
    Mclasse.save()
    context = {
        'MClasses': Mclasse,
        'ApprenClasse': ApprenClasse,
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'total_apprenants': total_apprenants,
    }
    messages.success(request, f'Elève:{request.POST.get("Matricule")}  ajouté avec succés')
    return render(request, 'LesClasses/AjouterApprClasse.html', context)

@login_required
def CodeInscrireApprClasses(request):

    if request.method == "POST":
        Mclasse = MaClasse.objects.filter(CodeAffect=request.POST.get("CodeInvitation")).first()
        if not Mclasse:
            messages.success(request, f'Code Invitation : {request.POST.get("CodeInvitation")} inexistant')
            return render(request, 'LesClasses/AjouterParCodeClasse.html')

        Codeinviter = request.POST.get("CodeInvitation")
        Appren = Apprenants.objects.filter(username_id=request.user.id).first()
        ApprenClasse = apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk,apprenant_id=Appren.Matricule)
        ApprenClasses = apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk)
        total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk).count()
        context = {

            'MClasses': Mclasse,
            'ApprenClasse': ApprenClasse,
            "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
            'total_apprenants': total_apprenants,
            'ApprenClasses':ApprenClasses
        }

        if not Appren:
            messages.success(request, f'Matricule : {Codeinviter} inexistant')
            return render(request, 'LesClasses/ListeApprClasse.html', context)

        # Quand le Niveau est different
        if Mclasse.Niveau != Appren.Niveau:
            messages.success(request, f"Cet élève : {Codeinviter} n'a pas le Niveau de la classe")
            return render(request, 'LesClasses/ListeApprClasse.html', context)

        if apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk, apprenant_id=Appren.Matricule).exists():
            messages.success(request, f'Elève:{request.user.id} déjà inscrit dans la Classe')
            return render(request, 'LesClasses/ListeApprClasse.html', context)

        inscription = apprenant_maclasses(
            apprenant_id=Appren.Matricule,
            maclasse_id=Mclasse.pk
        )
        inscription.save()
        total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk).count()
        context = {

            'MClasses': Mclasse,
            'ApprenClasse': ApprenClasse,
            "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
            'total_apprenants': total_apprenants,
            'ApprenClasses': ApprenClasses
        }
        if Mclasse :
            Mclasse.Effectif=total_apprenants
            Mclasse.save()

        messages.success(request, f'Elève:{Appren.Matricule}  ajouté avec succés')
        return render(request, 'LesClasses/ListeApprClasse.html', context)

@login_required
def AjouterParCode(request):
    if request.method == "POST":
        Mclasse = MaClasse.objects.filter(CodeAffect=request.POST.get("CodeInvitation")).first()
        if not Mclasse:
            messages.success(request, f'Code Invitation : {request.POST.get("CodeInvitation")} inexistant')
            return render(request, 'LesClasses/AjouterparCodeClasse.html')

        Codeinviter = request.POST.get("CodeInvitation")
        Appren = Apprenants.objects.filter(username_id=request.user.id).first()
        ApprenClasse = apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk, apprenant_id=Appren.Matricule)
        total_apprenants = apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk).count()
        context = {

            'MClasses': Mclasse,
            'ApprenClasse': ApprenClasse,
            "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
            'total_apprenants': total_apprenants,
        }

        if not Appren:
            messages.success(request, f'Matricule : {Codeinviter} inexistant')
            return render(request, 'LesClasses/AjouterparCodeClasse.html', context)

        # Quand le Niveau est different
        if Mclasse.Niveau != Appren.Niveau:
            messages.success(request, f"Cet élève : {Codeinviter} n'a pas le Niveau de la classe")
            return render(request, 'LesClasses/AjouterparCodeClasse.html', context)

        if apprenant_maclasses.objects.filter(maclasse_id=Mclasse.pk, apprenant_id=Appren.Matricule).exists():
            messages.success(request, f'Elève:{request.user.id} déjà inscrit dans la Classe')
            return render(request, 'LesClasses/AjouterparCodeClasse.html', context)

        inscription = apprenant_maclasses(
            apprenant_id=Appren.Matricule,
            maclasse_id=Mclasse.pk
        )
        inscription.save()
        messages.success(request, f'Elève:{Appren.Matricule}  ajouté avec succés')
        context = {
            'MClasses': Mclasse,
            'ApprenClasse': ApprenClasse,
            "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
            'total_apprenants': total_apprenants,
        }
        if Mclasse :
            Mclasse.Effectif=total_apprenants
            Mclasse.save()
        if global_variable == "Formateur":
            return render(request, 'LesClasses/AjouterparCodeClasse.html', context)
        else:
            return render(request, 'LesClasses/AjouterparCodeClasse.html', context)

    if global_variable == "Formateur" :
        return render(request, 'LesClasses/AjouterParCodeClasse.html')
    else:
        return render(request, 'LesClasses/AjouterparCodeClasseApp.html')


# DOCUMENTS CLASSES
@login_required
def classe_documents(request, pk): # Ancien Ajouter Document
    nom_session = request.session.get('compte')
    base_template = (
        "Menus/MenuEspaceForm.html" if nom_session == 'Formateur'
        else "Menus/MenuEspaceApp.html"
    )

    nomclasse = get_object_or_404(MaClasse, id=pk)
    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDoc = TypeDocument.objects.all()
    Types = nom_session
    DocClass = MesDocuments.objects.filter(maclasse_id=pk).order_by('-id')[:25]

    if request.method == 'POST':
        form = MesDocumentsForm(request.POST, request.FILES)
        if form.is_valid():
            # Vérifie que le niveau choisi correspond à la classe
            if str(nomclasse.Niveau) != str(form.cleaned_data['Niveau']):
                messages.error(
                    request,
                    f"Niveau de la classe ({nomclasse.Niveau}) non conforme au niveau choisi ({form.cleaned_data['Niveau']})."
                )
            else:
                document = form.save(commit=False)
                document.maclasse_id = pk
                document.username = request.user
                document.save()
                messages.success(request, "✅ Document ajouté avec succès.")
                return redirect('Ajouter_document', pk=pk)
        else:
            messages.error(request, "⚠️ Erreur dans le formulaire. Vérifiez les informations.")
    else:
        form = MesDocumentsForm()

    context = {
        'pk': pk,
        'nomclasse': nomclasse,
        'Types': Types,
        'disciple': disciple,
        'niveau': niveau,
        'TypeDoc': TypeDoc,
        'DocClass': DocClass,
        'base_template': base_template,
        'form': form,
    }

    return render(request, 'Documents/AjouterDocuments.html', context)

def Ajouter_document(request, classe_id):
    """
    Vue principale : liste paginée avec filtres + support DataTables client-side.
    """
    nom_session = request.session.get('compte')
    base_template = (
        "Menus/MenuEspaceForm.html" if nom_session == 'Formateur'
        else "Menus/MenuEspaceApp.html"
    )
    nomclasse = get_object_or_404(MaClasse, id=classe_id)  # adapte le modèle Classe
    qs = MesDocuments.objects.filter(maclasse_id=classe_id).order_by('-id')
    TypeDoc = TypeDocument.objects.all()
    # filtres (GET)
    q = request.GET.get('q', '').strip()
    discipline = request.GET.get('discipline', '')
    typedoc = request.GET.get('typedoc', '')

    if q:
        qs = qs.filter(
            Q(Titre__icontains=q) |
            Q(Discipline__icontains=q)
        )
    if discipline:
        qs = qs.filter(Discipline=discipline)
    if typedoc:
        qs = qs.filter(TypeDoc=typedoc)

    # Pagination Django classique
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 12)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    # distinct values for filter dropdowns
    disciplines = MesDocuments.objects.filter(maclasse_id=classe_id).values_list('Discipline', flat=True).distinct()
    typedocs = MesDocuments.objects.filter(maclasse_id=classe_id).values_list('TypeDoc', flat=True).distinct()
    if request.method == 'POST':
        form = MesDocumentsForm(request.POST, request.FILES)
        if form.is_valid():
            # Vérifie que le niveau choisi correspond à la classe
            if str(nomclasse.Niveau) != str(form.cleaned_data['Niveau']):
                messages.error(
                    request,
                    f"Niveau de la classe ({nomclasse.Niveau}) non conforme au niveau choisi ({form.cleaned_data['Niveau']})."
                )
            else:
                document = form.save(commit=False)
                document.maclasse_id =classe_id
                document.username = request.user
                document.save()
                messages.success(request, "✅ Document ajouté avec succès.")

                # return redirect('Ajouter_document', maclasse_id=classe_id)
        else:
            messages.error(request, "⚠️ Erreur dans le formulaire. Vérifiez les informations.")
    else:
        form = MesDocumentsForm()
    context = {
        'classe_id':classe_id,
        'nomclasse': nomclasse,
        'DocClass': page_obj,        # si tu gardes DocClass dans ton template existant
        'page_obj': page_obj,
        'paginator': paginator,
        'disciplines': disciplines,
        'typedocs': typedocs,
        'TypeDoc': TypeDoc,
        'q': q,
        'base_template': base_template,
        'form': form,
        'discipline_selected': discipline,
        'typedoc_selected': typedoc,
        # option pour DataTables server-side
        'datatable_ajax_url': request.build_absolute_uri(
            reverse('doc_list_data', args=[classe_id])
        ),
    }
    return render(request, 'Documents/AjouterDocument.html', context)

def doc_list_data(request, classe_id):
    """
    Retourne JSON pour DataTables en mode server-side.
    Gère : start, length, search[value], order, columns[i][data]
    """
    # Paramètres de DataTables
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    # Filtrage initial (par classe)
    qs = MesDocuments.objects.filter(maclasse_id=classe_id)

    # Recherche globale
    if search_value:
        qs = qs.filter(
            Q(Titre__icontains=search_value) |
            Q(Discipline__icontains=search_value) |
            Q(TypeDoc__icontains=search_value)
        )

    # tri (simple: récupère la première colonne d'ordre)
    order_col_index = request.GET.get('order[0][column]')
    order_dir = request.GET.get('order[0][dir]', 'asc')
    if order_col_index is not None:
        order_col = request.GET.get(f'columns[{order_col_index}][data]', 'id')
        if order_dir == 'desc':
            order_col = f'-{order_col}'
        qs = qs.order_by(order_col)
    else:
        qs = qs.order_by('-id')

    records_total = MesDocuments.objects.filter(maclasse_id=classe_id).count()
    records_filtered = qs.count()

    qs_page = qs[start:start + length]

    data = []
    for doc in qs_page:
        # adapte les champs selon ton modèle
        data.append({
            'Discipline': doc.Discipline,
            'Titre': doc.Titre,
            'TypeDoc': f"{doc.TypeDoc}-N°{doc.id}",
            'Document': doc.Document.url if doc.Document else '',
            'id': doc.id,
            # on peut aussi renvoyer HTML si souhaité (ex: boutons)
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    })

# Solution document CLASSE
@login_required
def Ajouter_Solution(request, pk):
    nom_session = request.session.get('compte', 'Inconnu')

    # Détermine le template de base selon le type d'utilisateur
    base_template = "Menus/MenuEspaceForm.html" if nom_session == 'Formateur' else "Menus/MenuEspaceApp.html"

    # Récupère le document
    DocClass = get_object_or_404(MesDocuments, id=pk)
    nomclasse = get_object_or_404(MaClasse, id=DocClass.maclasse_id)

    # Liste des solutions déjà déposées pour ce document
    solutions = SoluExoClasses.objects.filter(documents_id=DocClass.id)

    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDoc = TypeDocument.objects.all()

    # Prépare le contexte commun
    context = {
        'pk': pk,
        'nomclasse': nomclasse,
        'Types': nom_session,
        'disciple': disciple,
        'niveau': niveau,
        'TypeDoc': TypeDoc,
        'DocClass': DocClass,
        'Solution': solutions,
        'base_template': base_template,
    }

    # ----- POST -----
    if request.method == 'POST':
        form = SolutionExoForm(request.POST, request.FILES)
        if form.is_valid():
            # Vérifie la conformité du niveau
            niveau_choisi = form.cleaned_data.get('Niveau')
            if str(DocClass.Niveau) != str(niveau_choisi):
                messages.error(request, f"Niveau document : {DocClass.Niveau} non conforme au niveau choisi : {niveau_choisi}.")
                return render(request, 'Solution/AjouterSoluDocument.html', context)

            try:
                # Empêche le dépôt multiple par le même utilisateur
                existe = SoluExoClasses.objects.filter(documents_id=pk, username_id=request.user.id).exists()
                if existe:
                    messages.warning(request, "Vous avez déjà déposé une solution pour ce document.")
                    return render(request, 'Solution/AjouterSoluDocument.html', context)

                # Création de la solution
                solution = form.save(commit=False)
                solution.maclasse = DocClass.maclasse
                solution.username_id = request.user.id
                solution.documents_id = pk
                solution.save()

                messages.success(request, "✅ Solution ajoutée avec succès.")
                return redirect('Ajouter_Solution', pk=pk)

            except IntegrityError:
                messages.error(request, "⚠️ Une erreur est survenue, veuillez réessayer.")
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")

    # ----- GET -----
    else:
        form = SolutionExoForm()

    context['form'] = form
    return render(request, 'Solution/AjouterSoluDocument.html', context)

# Ajouter Note
def Ajouter_Note(request, pk):
    #doc = get_object_or_404(SoluExoClasses, pk=pk)
    doc = SoluExoClasses.objects.filter(pk=pk).first()
    # NivClasse = MaClasse.objects.get(id=doc.maclasse_id).Niveau
    # nom_session = request.session.get('Sesclasse', 'Inconnu')
    nom_session = request.session.get('compte')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
    DocClass = MesDocuments.objects.filter(id=doc.documents_id).first()
    nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    Solution = SoluExoClasses.objects.filter(documents_id=DocClass.id)
    # Solutions = SoluExoClasses.objects.filter(id=pk).first()
    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDoc = TypeDocument.objects.all()
    Types = request.session.get('compte')
    # form = SolutionExoForm(request.POST, instance=doc)
    context = {
        'pk': pk,
        'nomclasse': nomclasse,
        'Types': Types,
        'disciple': disciple,
        'niveau': niveau,
        'TypeDoc': TypeDoc,
        'DocClass': DocClass,
        'Solution': Solution,
        'base_template': base_template,
        'nom_session': nom_session,
        'doc':doc,
        # 'form': form,
    }
    if nom_session == 'Apprenant':
        messages.success(request, "Vous n'êtes pas autorisé à donner une Note.")
        return redirect('Ajouter_Solution', doc.documents_id)
    return render(request, 'Solution/AjouterNoteSoluDocument.html',context)

# Saisir des Notes
def notation(request, pk):
    solution = SoluExoClasses.objects.filter(id=pk).first()
    nom_session = request.session.get('compte')
    solution.Note=request.POST.get("Note")
    solution.save()
    return redirect('Ajouter_Note', pk)

# Supprimer Solution
@login_required
def SupSolution(request, pk):
    doc = SoluExoClasses.objects.filter(id=pk).first()
    request.session['Sesclasse'] = doc.maclasse_id
    nom_session = request.session.get('Sesclasse', 'Inconnu')

    context = {
        'pk': pk,
        'nom_session':nom_session,
       'doc': doc,
    }
    if doc.Note != 0:
        messages.success(request, "Vous ne pouvez plus supprimer une solution Notée.")
        return redirect('Ajouter_document', nom_session)

    if request.user.id != doc.username_id:
        messages.success(request, "Vous n'êtes pas autorisé à Supprimer ce Document.")
        return redirect('Ajouter_document', nom_session)
    if doc:
        doc.Solution.delete(save=False)  # supprime le fichier du disque
        doc.delete()

    #return render(request, 'Documents/AjouterDocuments.html', context)
    return redirect('Ajouter_document', nom_session)

def Modifier_document(request, pk):

    doc = get_object_or_404(MesDocuments, pk=pk)
    NivClasse = MaClasse.objects.get(id=doc.maclasse_id).Niveau
    nom_session = request.session.get('Sesclasse', 'Inconnu')

    nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    discipline = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDoc = TypeDocument.objects.all()
    Types = request.session.get('compte')
    DocClass = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id).order_by('id')
    qs = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id).order_by('-id')
    page_obj = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id).order_by('id')
    discipline = request.GET.get('discipline', '')
    typedoc = request.GET.get('typedoc', '')

    if request.user.id != doc.username_id:
        messages.success(request, "Vous n'êtes pas autorisé à Modifier ce Document.")
        return redirect('Modifier_document', nom_session)

    if doc.Document:
        ancien_fichier = doc.Document.name  # chemin relatif vers MEDIA

    else:
        ancien_fichier = None
    # Pagination
    # filtres (GET)
    q = request.GET.get('q', '').strip()
    discipline = request.GET.get('discipline', '')
    typedoc = request.GET.get('typedoc', '')

    # Filtres
    if q:
        qs = qs.filter(
            Q(Titre__icontains=q) |
            Q(Discipline__icontains=q)
        )

    if discipline:
        qs = qs.filter(Discipline=discipline)

    if typedoc:
        qs = qs.filter(TypeDoc=typedoc)

    # Pagination Django classique
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 12)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    # distinct values for filter dropdowns
    disciplines = MesDocuments.objects.filter(
        maclasse_id=doc.maclasse_id
    ).values_list("Discipline", flat=True).distinct()

    typedocs = MesDocuments.objects.filter(
        maclasse_id=doc.maclasse_id
    ).values_list("TypeDoc", flat=True).distinct()

    # Fin Pagination
    if request.method == 'POST':
        form = MesDocumentsForm(request.POST, request.FILES, instance=doc)

        if form.is_valid():
            # Supprimer l’ancien fichier si remplacé (dans la vue)
            if 'Document' in request.FILES and ancien_fichier:
                chemin_fichier = os.path.join(settings.MEDIA_ROOT, ancien_fichier)
                if os.path.isfile(chemin_fichier):
                    os.remove(chemin_fichier)
            if NivClasse != request.POST["Niveau"]:
                messages.success(request,
                                 f"Niveau Document Choisi: {request.POST["Niveau"]} n'est pas conforme au Niveau Classe:{NivClasse}")
                # return render(request, 'Documents/ModifierDocuments.html', {'form': form})
                return redirect('Modifier_document', nom_session)
            else:
                form.save()
                messages.success(request, "Document modifié avec succès.")
                return redirect('Modifier_document', doc.maclasse_id)
    else:
        form = MesDocumentsForm(instance=doc)
    context = {
        'pk': pk,
        'nomclasse': nomclasse,
        'Types': Types,
        'niveau': niveau,
        'TypeDoc': TypeDoc,
        'DocClass': DocClass,
        'form': form,
        'classe_id':doc.maclasse_id,
        'typedocs': typedocs,
        'q': q,
        'page_obj': page_obj,
        'paginator': paginator,
        'disciplines': disciplines,
        'discipline_selected': disciplines,
        'typedoc_selected': typedocs,
        # option pour DataTables server-side
        'datatable_ajax_url': request.build_absolute_uri(
            reverse('doc_list_data', args=[doc.maclasse_id])
        ),
    }
    return render(request, 'Documents/ModifierDocuments.html', context)

@login_required
def Transfert_document(request, pk): # Transfert vers Classe Formateur
    doc = get_object_or_404(MesDossiers, pk=pk)
    nom_session = request.session.get('compte')
    FormClass = MaClasse.objects.filter(username_id=request.user.id,Niveau=doc.Niveau)  # Mes classes
    GroupeEt = GroupeEtude.objects.filter(username_id=request.user.id, Niveau=doc.Niveau)  # Mes Groupe etude
    #print(GroupeEt.values())
    if doc.Document:
        ancien_fichier = doc.Document.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    if request.method == 'POST':
        #form = MesDocumentsForm(request.POST, request.FILES)
        NivClasse = MaClasse.objects.get(id=request.POST["idClasse"])
        form  = MesDocuments(
            Discipline_id=doc.Discipline,
            Niveau=doc.Niveau,
            TypeDoc=doc.TypeDoc,
            Titre=doc.Titre,
            Observation=doc.Observation,
            Etat=doc.Etat,
            Document=ancien_fichier,
            maclasse_id=request.POST["idClasse"],
            username_id=request.user.id,
        )
        #if form.is_valid():

        form.save()
        messages.success(request, "Document Transferé avec succès.")
        ListeDossiers = MesDocuments.objects.filter(maclasse_id=request.POST["idClasse"])
        context = {
            'form': form,
            'FormClass': FormClass,
            'Types': nom_session,
            'doc': doc,
            # 'GroupeEt': GroupeEt,
            'ListeDossiers': ListeDossiers,
        }
        #return redirect('Ajouter_dossiers', request.user.id)
        return render(request, 'Documents/TransfertDocument.html', context)
    #else:
    form = MesDocumentsForm(instance=doc)

    context = {
        'form': form,
        'FormClass': FormClass,
        'Types': nom_session,
        'doc': doc,
        # 'GroupeEt': GroupeEt,

    }
    # if nom_session=='Formateur':
    return render(request, 'Documents/TransfertDocument.html',context)
    # if nom_session=='Apprenant':
    #      return render(request, 'GroupeEtude/TransfertDocumentGrpEtude.html',context)


def Update_document(request, pk):  # Mettre à jour document
    doc = MesDocuments.objects.filter(id=pk).first()
    disciple = Discipline.objects.all()
    #niveau=Niveau.objects.all()
    TypeDoc = TypeDocument.objects.all()
    DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    Mclasse = MesDocumentsForm(request.POST, instance=doc)
    context = {
        'pk': pk,
        #'nomclasse': nomclasse,
        # 'form': form,
        'disciple': disciple,
        #'niveau': niveau,
        'TypeDoc': TypeDoc,
        'DocClass': DocClass
    }

    Document = MesDocuments(
        Discipline=request.POST.get("Discipline"),
        Niveau=request.POST.get("Niveau"),
        TypeDoc=request.POST.get("TypeDoc"),
        Titre=request.POST.get("Titre"),
        Observation=request.POST.get("Observation"),
        Etat=request.POST.get("Etat"),
        Document=request.FILES.get("document"),
        maclasse_id=pk,
        username_id=request.user.id,
    )
    Document.save()
    messages.success(request, "Document Modifié avec succès.")
    return redirect('Ajouter_document', doc.maclasse_id)


def SupDocuments(request, pk):
    doc = MesDocuments.objects.filter(id=pk).first()
    nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDoc = TypeDocument.objects.all()
    DocClass = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id)  # Document à supprimer
    DocDossier=MesDossiers.objects.filter(Document=doc.Document)
    Docgroup=DossiersGRPTrav.objects.filter(Document=doc.Document)
    context = {
        'pk': pk,
        'nomclasse': nomclasse,
        # 'form': form,
        'disciple': disciple,
        'niveau': niveau,
        'TypeDoc': TypeDoc,
        'DocClass': DocClass
    }

    if request.user.id != doc.username_id:
        messages.success(request, "Vous n'êtes pas autorisé à Supprimer ce Document.")
        return redirect('Ajouter_document', doc.maclasse_id)
    if not DocDossier or not Docgroup:
        doc.Document.delete(save=False)  # supprime le fichier du disque
        doc.delete()
    else:
        doc.delete()
    #return render(request, 'Documents/AjouterDocuments.html', context)
    return redirect('Ajouter_document', doc.maclasse_id)

# MESSAGES DES CLASSES

def Ajouter_MessagesClasse(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    # nom_session = request.session.get('compte', 'Inconnu')
    nom_session = request.session.get('compte', 'Inconnu')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
        MesClasse = MaClasse.objects.filter(username_id=request.user.id)
        MessagesClasses = Message_Classes.objects.filter(username_id=request.user.id).order_by('-create_at')
        TotalMessages = Message_Classes.objects.filter(username_id=request.user.id).count()

    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
        #appren = get_object_or_404(Apprenants, username_id=request.user.id)
        # MesClassAppr=apprenant_maclasses.objects.filter(apprenant_id=appren.Matricule)
        # MesClasse = MaClasse.objects.filter(id__in=MesClassAppr.values_list('maclasse_id', flat=True))
        # #print(MesClasse.values())
        # MessagesClasses = Message_Classes.objects.filter(username_id=request.user.id).order_by('-create_at')[:10]
        # TotalMessages = Message_Classes.objects.filter(username_id=request.user.id).count()
        appren = Apprenants.objects.filter(username_id=pk).first()  # Choix de l'apprenant
        MesClassAppr=apprenant_maclasses.objects.filter(apprenant_id=appren.Matricule) # Selection de don Groupe
        # Selection des groupes parents
        MesClasse = MaClasse.objects.filter(id__in=MesClassAppr.values_list('maclasse_id', flat=True))
        paginator = Paginator(MesClasse, 15)  # 15 réunions par page
        page_number = request.GET.get('page')
        page_objClass = paginator.get_page(page_number)

        MessagesClasses = Message_Classes.objects.filter(
            maclasse_id__in=MesClasse.values_list('id', flat=True)).order_by('-create_at')
        paginator = Paginator(MessagesClasses, 10)  # 10 réunions par page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        TotalMessages = MessagesClasses.count()


    #ListeMessage=Message_Classes.objects.filter(username_id=request.user.id).order_by('-create_at')
    # disciple = Discipline.objects.all()
    # niveau = Niveau.objects.all()
    # TypeDocs = TypeDocument.objects.all()

    if request.method == 'POST':
        Messages = Message_Classes(
            Objet=request.POST.get("Objet"),
            Message = request.POST.get("Message"),
            PiecesJointe = request.FILES.get("PiecesJointe"),
            maclasse_id = request.POST.get("Classe"),
            username_id=request.user.id,
        )

        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages':TotalMessages,
            "Types": nom_session,
            'MesClasse':  page_objClass,
            'MessagesClasses': page_obj,
            'base_template': base_template,

        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        return redirect('Ajouter_MessagesClasse', request.user.id)

    else:
        form = MessageClasseForm
        context = {
            'pk': pk,
            "Types": nom_session,
            'MesClasse': page_objClass,
            'MessagesClasses': page_obj,
            'TotalMessages': TotalMessages,
            'base_template': base_template,
            'form':form,
        }
        return render(request, 'Messages/MessagesClasses.html', context)

# Supprimer message
def Supp_MessagesClasse(request, pk):
    nom_session = request.session.get('compte', 'Inconnu')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
        MesClasse = MaClasse.objects.filter(username_id=request.user.id)
        MessagesClasses = Message_Classes.objects.filter(username_id=request.user.id).order_by('-create_at')[:15]
        TotalMessages = Message_Classes.objects.filter(username_id=request.user.id).count()

    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
        appren = get_object_or_404(Apprenants, username_id=request.user.id)
        MesClassAppr = apprenant_maclasses.objects.filter(apprenant_id=appren.Matricule)
        MesClasse = MaClasse.objects.filter(id__in=MesClassAppr.values_list('maclasse_id', flat=True))
        MessagesClasses = Message_Classes.objects.filter(maclasse_id=pk).order_by('-create_at')[:15]
        TotalMessages = Message_Classes.objects.filter(maclasse_id=pk).count()
    LeMessage=Message_Classes.objects.filter(id=pk)
    # disciple = Discipline.objects.all()
    # niveau = Niveau.objects.all()
    # TypeDocs = TypeDocument.objects.all()
    # MesClasse = MaClasse.objects.filter(username_id=request.user.id)
    # MessagesClasses=Message_Classes.objects.filter(username_id=request.user.id).order_by('-create_at')

    LeMessage.delete()
    context = {
        'pk': pk,
        'LeMessage':LeMessage,
        "Types": nom_session,
        'MesClasse': MesClasse,
        'MessagesClasses': MessagesClasses,
        }
    messages.success(request, "Message Supprimer avec succès.")
    #return render(request, 'Documents/AjouterDossier.html', context)
    return redirect('Ajouter_MessagesClasse', request.user.id)

           #return render(request, 'Messages/MessagesClasses.html', context)

#Message Classe
def Liste_MessagesClasse(request, pk):
    nom_session = request.session.get('compte', 'Inconnu')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        Types = get_object_or_404(Formateurs, username_id=request.user.id).Type
        MesClasse = MaClasse.objects.filter(username_id=request.user.id)
        MessagesClasses = Message_Classes.objects.filter(maclasse_id=pk).order_by('-create_at')[:15]
        TotalMessages = Message_Classes.objects.filter(maclasse_id=pk).count()

    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
        appren = get_object_or_404(Apprenants, username_id=request.user.id)
        MesClassAppr = apprenant_maclasses.objects.filter(apprenant_id=appren.Matricule)
        MesClasse = MaClasse.objects.filter(id__in=MesClassAppr.values_list('maclasse_id', flat=True))
        MessagesClasses = Message_Classes.objects.filter(maclasse_id=pk ).order_by('-create_at')[:15]
        TotalMessages = Message_Classes.objects.filter(maclasse_id=pk).count()


    if request.method == 'POST':
        Messages = Message_Classes(
            Objet=request.POST.get("Objet"),
            Message = request.POST.get("Message"),
            PiecesJointe = request.FILES.get("PiecesJointe"),
            maclasse_id = request.POST.get("Classe"),
            username_id=request.user.id,
        )
        Messages.save()
        context = {
            'pk': pk,
            "Types": nom_session,
            'MesClasse': MesClasse,
            'MessagesClasses': MessagesClasses,
            'TotalMessages': TotalMessages,
            'base_template': base_template,
        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
         #return redirect('Ajouter_MessagesClasse', context)
    context = {
        'pk': pk,
        "Types": nom_session,
        'MesClasse': MesClasse,
        'MessagesClasses': MessagesClasses,
        'TotalMessages': TotalMessages,
        'base_template': base_template,
    }
    return render(request, 'Messages/MessagesClasses.html', context)

@login_required
def MesMessages(request):
    nom_session = request.session.get('compte', 'Inconnu')
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
        Types=get_object_or_404(Formateurs, username_id=request.user.id).Type
    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        Types = get_object_or_404(Apprenants, username_id=request.user.id).Type
    context = {
        "Types": Types,
        'base_template': base_template,
    }
    return render(request, 'Messages/MesMessages.html', context)

# ===================MES MESSAGES DE GROUPE DE TRAVIL================================================
def Ajouter_MessagesGroupeTrav(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # MesGroupes = GroupeTravails.objects.filter(username_id=request.user.id)
    # MessagesGrp=Message_GroupeTravail.objects.filter(username_id=request.user.id).order_by('-create_at')
    # TotalMessages = Message_GroupeTravail.objects.filter(username_id=request.user.id).count()
    forma = Formateurs.objects.filter(username_id=pk).first()  # Choix de l'apprenant
    MesGroupesForm = form_grpe_travails.objects.filter(Matricule_id=forma.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    MesGroupes = GroupeTravails.objects.filter(Q(id__in=MesGroupesForm.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
    MessagesGrp = Message_GroupeTravail.objects.filter(
        groupetravail_id__in=MesGroupes.values_list('id', flat=True)).order_by('-create_at')
    TotalMessages = MessagesGrp.count()
    Disc=Discipline.objects.all()

    if request.method == 'POST':
        Messages = Message_GroupeTravail(
            Objet=request.POST.get("Objet"),
            Message = request.POST.get("Message"),
            PiecesJointe = request.FILES.get("PiecesJointe"),
            groupetravail_id=request.POST.get("Groupe"),
            username_id=request.user.id,


        )

        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages':TotalMessages,
            "Types": nom_session,
            'MesGroupes':  MesGroupes,
            'MessagesGrp': MessagesGrp,
            'Disc': Disc,

        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        return redirect('Ajouter_MessagesGroupeTrav', request.user.id)

    else:
       # form = MessageClasseForm
        context = {
            'pk': pk,
            'TotalMessages': TotalMessages,
            "Types": nom_session,
            'MesGroupes': MesGroupes,
            'MessagesGrp': MessagesGrp,
            'Disc': Disc,
        }
        return render(request, 'Messages/MessagesGrpTrav.html', context)

# MES MESSAGES DE GROUPE DE TRAVIL
def Liste_MessagesGrpTrav(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    MesGroupes = GroupeTravails.objects.filter(username_id=request.user.id)
    MessagesGrp =Message_GroupeTravail.objects.filter(groupetravail_id=pk).order_by('-create_at')
    TotalMessages = Message_GroupeTravail.objects.filter(groupetravail_id=pk).count()
    if request.method == 'POST':
        Messages = Message_GroupeTravail(
            Objet=request.POST.get("Objet"),
            Message=request.POST.get("Message"),
            PiecesJointe=request.FILES.get("PiecesJointe"),
            groupetravail_id=request.POST.get("Groupe"),
            username_id=request.user.id,
        )
        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages': TotalMessages,
            "Types": nom_session,
            'MesGroupes': MesGroupes,
            'MessagesGrp': MessagesGrp,
        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        #return redirect('Ajouter_MessagesGroupeTrav', context)
        return render(request, 'Messages/MessagesGrpTrav.html', context)
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes': MesGroupes,
        'MessagesGrp': MessagesGrp,
    }
    return render(request, 'Messages/MessagesGrpTrav.html', context)

def Liste_MessagesParGrpTrav(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # MesGroupes = GroupeEtude.objects.filter(username_id=request.user.id)
    # MessagesEtude =Message_GroupeEtude.objects.filter(groupeetude_id=pk).order_by('-create_at')
    # TotalMessages = Message_GroupeEtude.objects.filter(groupeetude_id=pk).count()
    #-----------------------------
    forma = Formateurs.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = form_grpe_travails.objects.filter(Matricule_id=forma.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    #MesGroupes = GroupeTravails.objects.filter(id__in=MesGroupe.values_list('groupetravail_id', flat=True))
    MesGroupes = GroupeTravails.objects.filter(
        Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
    paginator = Paginator(MesGroupes, 15)  # 10 réunions par page
    page_number = request.GET.get('page')
    page_objGrp = paginator.get_page(page_number)

    groupe = GroupeTravails.objects.filter(id=pk)
    MessagesGrp = Message_GroupeTravail.objects.filter(groupetravail_id=pk).order_by('-create_at')
    paginator = Paginator(MessagesGrp, 15)  # 10 réunions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    TotalMessages = MessagesGrp.count()
    if request.method == 'POST':
        Messages = Message_GroupeEtude(
            Objet=request.POST.get("Objet"),
            Message=request.POST.get("Message"),
            PiecesJointe=request.FILES.get("PiecesJointe"),
            groupeetude_id=request.POST.get("Groupe"),
            username_id=request.user.id,
        )
        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages': TotalMessages,
            "Types": nom_session,
            'MesGroupes':  page_objGrp,
            'MessagesGrp': page_obj,
            'groupe':groupe,
        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        #return redirect('Ajouter_MessagesGroupeTrav', context)
        return render(request, 'Messages/MessagesGrpTrav.html', context)
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes':  page_objGrp,
        'MessagesGrp': page_obj,
        'groupe':groupe,
    }
    return render(request, 'Messages/MessagesGrpTrav.html', context)

#Suppression des messages groupe
def Supp_MessagesGrpTrav(request, pk):

    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    LeMessage=Message_GroupeTravail.objects.filter(id=pk)
    MesGroupes = GroupeTravails.objects.filter(username_id=request.user.id)
    MessagesGrp = Message_GroupeTravail.objects.filter(username_id=request.user.id).order_by('-create_at')
    TotalMessages = Message_GroupeTravail.objects.filter(username_id=request.user.id).count()

    LeMessage.delete()
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes': MesGroupes,
        'MessagesGrp': MessagesGrp,
        }
    messages.success(request, "Message Supprimer avec succès.")
    return redirect('Ajouter_MessagesGroupeTrav', request.user.id)

# ===================MES MESSAGES DE GROUPE DE ETUDE================================================
def Ajouter_MessagesGroupeEtude(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    Appren = Apprenants.objects.filter(username_id=request.user.id).first() #Choix de l'apprenant
    MesGroupe =Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule) #Selection de don Groupe

    # Selection des groupes parents
    MesGroupes = GroupeEtude.objects.filter(Q(id__in=MesGroupe.values_list('groupetude_id', flat=True))|Q(username_id=request.user.id))
    paginator = Paginator( MesGroupes, 15)  # 15 réunions par page
    page_number = request.GET.get('page')
    page_objGrp = paginator.get_page(page_number)

    MessagesEtude=Message_GroupeEtude.objects.filter(groupeetude_id__in= MesGroupes.values_list('id', flat=True)).order_by('-create_at')
    paginator = Paginator( MessagesEtude, 10)  # 10 réunions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    TotalMessages =  MessagesEtude.count()
    if request.method == 'POST':
        Messages = Message_GroupeEtude(
            Objet=request.POST.get("Objet"),
            Message = request.POST.get("Message"),
            PiecesJointe = request.FILES.get("PiecesJointe"),
            groupeetude_id=request.POST.get("Groupe"),
            username_id=request.user.id,
        )

        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages':TotalMessages,
            "Types": nom_session,
            'MesGroupes': page_objGrp,
            'MessagesEtude': page_obj,

        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        return redirect('Ajouter_MessagesGroupeEtude', request.user.id)

    else:
       # form = MessageClasseForm
        context = {
            'pk': pk,
            'TotalMessages': TotalMessages,
            "Types": nom_session,
            'MesGroupes': page_objGrp,
            'MessagesEtude': page_obj,
        }
        return render(request, 'Messages/MessagesGrpEtude.html', context)

# MES MESSAGES DE GROUPE DE ETUDE
def Liste_MessagesGrpEtude(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # MesGroupes = GroupeEtude.objects.filter(username_id=request.user.id)
    # MessagesEtude =Message_GroupeEtude.objects.filter(groupeetude_id=pk).order_by('-create_at')
    # TotalMessages = Message_GroupeEtude.objects.filter(groupeetude_id=pk).count()
    #-----------------------------
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    MesGroupes = GroupeEtude.objects.filter(id__in=MesGroupe.values_list('groupetude_id', flat=True))
    MessagesEtude = Message_GroupeEtude.objects.filter(
        groupeetude_id__in=MesGroupes.values_list('id', flat=True)).order_by('-create_at')
    TotalMessages = MessagesEtude.count()
    if request.method == 'POST':
        Messages = Message_GroupeEtude(
            Objet=request.POST.get("Objet"),
            Message=request.POST.get("Message"),
            PiecesJointe=request.FILES.get("PiecesJointe"),
            groupeetude_id=request.POST.get("Groupe"),
            username_id=request.user.id,
        )
        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages': TotalMessages,
            "Types": nom_session,
            'MesGroupes': MesGroupes,
            'MessagesEtude': MessagesEtude,
        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        #return redirect('Ajouter_MessagesGroupeTrav', context)
        return render(request, 'Messages/MessagesGrpEtude.html', context)
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes': MesGroupes,
        'MessagesEtude': MessagesEtude,
    }
    return render(request, 'Messages/MessagesGrpEtude.html', context)

# Liste des messages par groupe
def Liste_MessagesParGrpEtude(request, pk):
    #nomclasse = MaClasse.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # MesGroupes = GroupeEtude.objects.filter(username_id=request.user.id)
    # MessagesEtude =Message_GroupeEtude.objects.filter(groupeetude_id=pk).order_by('-create_at')
    # TotalMessages = Message_GroupeEtude.objects.filter(groupeetude_id=pk).count()
    #-----------------------------
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    MesGroupes = GroupeEtude.objects.filter(Q(id__in=MesGroupe.values_list('groupetude_id', flat=True))|Q(username_id=request.user.id))
    paginator = Paginator(MesGroupes, 15)  # 10 réunions par page
    page_number = request.GET.get('page')
    page_objGrp = paginator.get_page(page_number)

    groupe = GroupeEtude.objects.filter(id=pk).first()
    MessagesEtude = Message_GroupeEtude.objects.filter(groupeetude_id=pk).order_by('-create_at')
    TotalMessages = MessagesEtude.count()
    if request.method == 'POST':
        Messages = Message_GroupeEtude(
            Objet=request.POST.get("Objet"),
            Message=request.POST.get("Message"),
            PiecesJointe=request.FILES.get("PiecesJointe"),
            groupeetude_id=request.POST.get("Groupe"),
            username_id=request.user.id,
        )
        Messages.save()
        context = {
            'pk': pk,
            'TotalMessages': TotalMessages,
            "Types": nom_session,
            'MesGroupes': page_objGrp,
            'MessagesEtude': MessagesEtude,
            'groupe':groupe,
        }
        messages.success(request, "Message ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        #return redirect('Ajouter_MessagesGroupeTrav', context)
        return render(request, 'Messages/MessagesGrpEtude.html', context)
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes': page_objGrp,
        'MessagesEtude': MessagesEtude,
        'groupe':groupe,
    }
    return render(request, 'Messages/MessagesGrpEtude.html', context)
#Suppression des messages groupe
def Supp_MessagesGrpEtude(request, pk):

    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    LeMessage=Message_GroupeEtude.objects.filter(id=pk).first()
    # MesGroupes = GroupeEtude.objects.filter(username_id=request.user.id)
    # MessagesEtude = Message_GroupeEtude.objects.filter(username_id=request.user.id).order_by('-create_at')
    # TotalMessages = Message_GroupeEtude.objects.filter(username_id=request.user.id).count()
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    MesGroupes = GroupeEtude.objects.filter(id__in=MesGroupe.values_list('groupetude_id', flat=True))
    MessagesEtude = Message_GroupeEtude.objects.filter(
        groupeetude_id__in=MesGroupes.values_list('id', flat=True)).order_by('-create_at')
    TotalMessages = MessagesEtude.count()
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes': MesGroupes,
        'MessagesEtude': MessagesEtude,
    }

    if  LeMessage.username_id != request.user.id:
        messages.success(request, "Vous n'avez pas le droit de Supprimer")
        return redirect('Ajouter_MessagesGroupeEtude', request.user.id )
    LeMessage.delete()
    context = {
        'pk': pk,
        'TotalMessages': TotalMessages,
        "Types": nom_session,
        'MesGroupes': MesGroupes,
        'MessagesEtude': MessagesEtude,
        }
    messages.success(request, "Message Supprimer avec succès.")
    return redirect('Ajouter_MessagesGroupeEtude', request.user.id)

#==================== Gestion des dossFormateur Professeurs==============================
def ListeDossiersPartType(request,pk,type_doc):
    # nomclasse = MaClasse.objects.get(id=pk)
    if request.method == 'POST':
        ListeDossiers = MesDossiers.objects.filter(username_id=request.user.id,TypeDoc_id=type_doc,Niveau_id=request.POST.get("Niveau")).order_by('id')
        TotalDossiers = MesDossiers.objects.filter(username_id=request.user.id, TypeDoc_id=type_doc,
                                                   Niveau_id=request.POST.get("Niveau")).count()
        Class=request.POST.get("Niveau")
    else:
        ListeDossiers = MesDossiers.objects.filter(username_id=request.user.id, TypeDoc_id=type_doc).order_by('id')
        TotalDossiers = MesDossiers.objects.filter(username_id=request.user.id, TypeDoc_id=type_doc).count()
        Class=""

    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    # DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    context = {
            'pk': pk,
            # 'nomclasse': nomclasse,
            # 'form': form,
            'disciple': disciple,
            'niveau': niveau,
            # 'DocClass': DocClass
            'TypeDocs': TypeDocs,
            'ListeDossiers': ListeDossiers,
            'type_doc': type_doc,
            'Class':Class,
            'TotalDossiers':TotalDossiers,
        }
    return render(request, 'Documents/ListeDossierParType.html', context)

def ListeDossiersPartType(request,pk,type_doc):
    # nomclasse = MaClasse.objects.get(id=pk)
    if request.method == 'POST':
        ListeDossiers = MesDossiers.objects.filter(username_id=request.user.id,TypeDoc_id=type_doc,Niveau_id=request.POST.get("Niveau")).order_by('id')
        TotalDossiers = MesDossiers.objects.filter(username_id=request.user.id, TypeDoc_id=type_doc,
                                                   Niveau_id=request.POST.get("Niveau")).count()
        Class=request.POST.get("Niveau")
    else:
        ListeDossiers = MesDossiers.objects.filter(username_id=request.user.id, TypeDoc_id=type_doc).order_by('id')
        TotalDossiers = MesDossiers.objects.filter(username_id=request.user.id, TypeDoc_id=type_doc).count()
        Class=""

    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    # DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    context = {
            'pk': pk,
            # 'nomclasse': nomclasse,
            # 'form': form,
            'disciple': disciple,
            'niveau': niveau,
            # 'DocClass': DocClass
            'TypeDocs': TypeDocs,
            'ListeDossiers': ListeDossiers,
            'type_doc': type_doc,
            'Class':Class,
            'TotalDossiers':TotalDossiers,
        }
    return render(request, 'Documents/ListeDossierParType.html', context)



def tailledossier_utilisee(user):
    total = MesDossiers.objects.filter(username_id=user).aggregate(Sum('taille'))['taille__sum']
    return total or 0

@login_required
def Ajouter_dossiers(request, pk):
    """
    Vue pour ajouter un dossier (document) à partir du formulaire MesDossiersForm.
    """

    # Gestion du menu selon le type de compte
    global Quota
    nom_session = request.session.get('compte', 'Inconnu')
    base_template = (
        "Menus/MenuEspaceForm.html" if nom_session == 'Formateur'
        else "Menus/MenuEspaceApp.html"
    )

    # Récupération des données utiles
    ListeDossiers = MesDossiers.objects.filter(username=request.user).order_by('-id')
    paginator = Paginator(ListeDossiers, 10)  # 10 réunions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if nom_session=="Formateur":
        Quota=Formateurs.objects.filter(username=request.user).first().QuotaDossier

    if nom_session=="Apprenant":
        Quota = Apprenants.objects.filter(username=request.user).first().QuotaDossier

    taille_utilisee=tailledossier_utilisee(request.user)  # Taille du modele MesDossiers
    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    TotalDossiers = ListeDossiers.count()
    restant=Quota- taille_utilisee
    if request.method == 'POST':
        # Verifie si la taille à Ajouter
        fichier = request.FILES["Document"]

        TailleFichiers = taillefichier(fichier)
        # print(taille_utilisee + TailleFichier)
        # print(Quota)
        if taille_utilisee + TailleFichiers > Quota:

            messages.error(request, "Vous avez atteint votre quota de stockage.")
            # Notification email
            send_mail(
                "Quota de stockage atteint",
                "Votre espace de stockage est plein. Merci de supprimer des fichiers,ou augmenter votre quota de stockage.",
                "ettien.assoumou@gmail.com",
                [request.user.email],
                fail_silently=True,
            )

            return redirect('Ajouter_dossiers', request.user.id)

        form = MesDossiersForm(request.POST, request.FILES)
        if form.is_valid():
            dossier = form.save(commit=False)
            dossier.username = request.user  # utilisateur connecté
            dossier.taille = TailleFichiers  # ici on attribue la taille du fichier
            dossier.save()
            messages.success(request, "✅ Document ajouté avec succès.")
            return redirect('Ajouter_dossiers', request.user.id)
        else:
            messages.error(request, "⚠️ Erreur dans le formulaire. Vérifiez les champs.")
    else:
        form =MesDossiersForm()

    context = {
        'pk': pk,
        'form': form,
        'disciple': disciple,
        'niveau': niveau,
        'TypeDocs': TypeDocs,
        'ListeDossiers': page_obj,
        'TotalDossiers': TotalDossiers,
        'Types': nom_session,
        'base_template': base_template,
        'taille_utilisee':taille_utilisee,
        'Mo_taille_utilisee':taille_utilisee/1024,
        'Quota': Quota,
        'Mo_Quota': Quota/1024,
        'restant':restant,
        'Mo_restant':restant/1024,
        "pourcentage": round((taille_utilisee / Quota) * 100, 2),
    }

    return render(request, 'Documents/AjouterDossier.html', context)



# Dossiers
@login_required
def Modifier_Dossiers(request, pk):
    """
    Permet à l'utilisateur de modifier un dossier existant.
    """

    dossier = get_object_or_404(MesDossiers, id=pk, username=request.user)
    nom_session = request.session.get('compte', 'Inconnu')
    MesDos = MesDossiers.objects.filter(username=request.user).order_by('-id')
    base_template = (
        "Menus/MenuEspaceForm.html" if nom_session == 'Formateur'
        else "Menus/MenuEspaceApp.html"
    )

    if request.method == 'POST':
        form = MesDossiersForm(request.POST, request.FILES, instance=dossier)
        dossier.taille = dossier.Document.size  # ici on attribue la taille du fichier
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Dossier modifié avec succès.")
            return redirect('Ajouter_dossiers', request.user.id)
        else:
            messages.error(request, "⚠️ Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = MesDossiersForm(instance=dossier)

    context = {
        'form': form,
        'dossier': dossier,
        'base_template': base_template,
        'Types': nom_session,
        'MesDos':MesDos,
    }

    return render(request, 'Documents/ModifierDossiers.html', context)

@login_required
def SupDossiers(request, pk):
    doc = MesDossiers.objects.filter(id=pk).first()
    #nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    #disciple = Discipline.objects.all()
    #niveau = Niveau.objects.all()
    #TypeDoc = TypeDocument.objects.all()
    #DocClass = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id)  # Document à supprimer
    context = {
        'pk': pk,

    }
    doc.Document.delete(save=False)  # supprime le fichier du disque
    doc.delete()
    #return render(request, 'Documents/AjouterDocuments.html', context)
    messages.success(request, f"Document N°: {pk} supprimé avec succès.")
    return redirect('Ajouter_dossiers',request.user.id)


@login_required
def GroupeTrav(request):

    form=GroupeTravailForm()
    # Mesgroupes=GroupeTravails.objects.filter( username_id=request.user.id).order_by('id')
    forma = Formateurs.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = form_grpe_travails.objects.filter(Matricule_id=forma.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    Mesgroupes = GroupeTravails.objects.filter(Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
    Disc = Discipline.objects.all()
    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'form':form,
        'username':get_object_or_404(Formateurs, username_id=request.user.id).username,
        'Mesgroupes':Mesgroupes,
        'Disc':Disc,
    }
    try:
        if request.method == 'POST':
            GroupeTravail = GroupeTravails(
                Groupe=request.POST.get("NomGroupe"),
                Responsable = request.POST.get("Responsable"),
                Contact = request.POST.get("Contact"),
                Discipline_id=request.POST.get("Discipline"),
                logo = request.FILES.get("logo"),
                CodeAffect = request.POST.get("CodeAffect"),
                username_id = request.user.id,


            )
            GroupeTravail.save()
            messages.success(request, f"Groupe de travail: crée avec succès.")
            context = {
                    "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
                    'form': form,
                    'Mesgroupes': Mesgroupes,
                    'Disc': Disc,
                }
    except IntegrityError:
        messages.success(request, "Désolé !!!,Le code d'invitation est dèjà utilisé.")
        #return render(request, 'GroupeTravail/GroupeTravail.html', context)

    return render(request, 'GroupeTravail/GroupeTravail.html', context)

#Modifier Groupe de travail
@login_required
def ModifGroupeTrav(request,pk):
    Mesgroupes = GroupeTravails.objects.filter(username_id=request.user.id)
    groups=GroupeTravails.objects.filter( id=pk).first()
    form=GroupeTravailForm(instance=groups)

    if groups.logo:
        ancien_fichier = groups.logo.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'form':form,
        'username':get_object_or_404(Formateurs, username_id=request.user.id).username,
        'Mesgroupes':Mesgroupes,
        'groups': groups,
        'pk':pk,
    }
    try:
        if request.method == 'POST':  # On verifie le code d'affectation
            codeAff = GroupeTravails.objects.filter(CodeAffect=request.POST.get("CodeAffect")).first()
            if (codeAff and groups.pk != codeAff.pk):
                messages.success(request, f"Ce Code {request.POST.get("CodeAffect")}: est déjà utilisé.")
                return render(request, 'GroupeTravail/ModifGroupeTravail.html', context)
        if request.method == 'POST':
            form = GroupeTravailForm(request.POST, request.FILES, instance=groups)
            if 'logo' in request.FILES and ancien_fichier:
                chemin_fichier = os.path.join(settings.MEDIA_ROOT, ancien_fichier)
                if os.path.isfile(chemin_fichier):
                    os.remove(chemin_fichier)

            #)
            form.save()
            messages.success(request, f"Groupe de travail: Modifié avec succès.")
            context = {
                "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
                'form': form,
                'username': get_object_or_404(Formateurs, username_id=request.user.id).username,
                'Mesgroupes': Mesgroupes,
                'groups': groups,
                'pk': pk,
                }
    except IntegrityError:
        messages.success(request, "Désolé !!!,Le code d'invitation est dèjà utilisé.")
        #return render(request, 'GroupeTravail/GroupeTravail.html', context)
    return render(request, 'GroupeTravail/ModifGroupeTravail.html', context)

@login_required
def SupGroupeTrav(request, pk):
    groups=GroupeTravails.objects.filter( id=pk).first()
    #nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    #disciple = Discipline.objects.all()
    #niveau = Niveau.objects.all()
    #TypeDoc = TypeDocument.objects.all()
    #DocClass = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id)  # Document à supprimer
    context = {
        'pk': pk,

    }
    groups.logo.delete(save=False)  # supprime le fichier du disque
    groups.delete()
    #return render(request, 'Documents/AjouterDocuments.html', context)
    messages.success(request, f"Groupe N°: {pk} supprimé avec succès.")
    return redirect('GroupeTrav')

@login_required
def AjouterFormGrpTrav(request, pk):
    groupes = GroupeTravails.objects.filter(id=pk).first()
    total_groupe = form_grpe_travails.objects.filter(groupetravail=pk).count()
    Membregroupe = form_grpe_travails.objects.filter(groupetravail=pk)

    context = {
        'Membregroupe': Membregroupe,
        'groupes': groupes,
        'total_groupe': total_groupe,
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type
    }
    try:
        if request.method == 'POST':
            Format = Formateurs.objects.filter(Matricule=request.POST.get("Matricule")).exists()
            if not Format:
                messages.success(request, f"Matricule N°: {request.POST.get("Matricule")} n'existe pas.")
                return render(request, 'GroupeTravail/AjouterFormGrpTrav.html', context)
            else:
               # FormatGrpT = form_grpe_travails.objects.get(Matricule=request.POST.get("Matricule"),groupetravail=pk)
                #if not FormatGrpT:
               form = form_grpe_travails(
                   Matricule_id=request.POST.get("Matricule"),
                   groupetravail_id=pk,
               )
            form.save()
            messages.success(request, f"Matricule N°: {request.POST.get("Matricule")} ajouté avec succès.")
            #return render(request, 'GroupeTravail/AjouterFormGrpTrav.html', context)
    except IntegrityError:
            messages.success(request, f"Matricule N°: {request.POST.get("Matricule")} existe déjà dans le Groupe.")
    return render(request, 'GroupeTravail/AjouterFormGrpTrav.html', context)

@login_required
def SupMembreGroupeTrav(request, pk):
    membre=form_grpe_travails.objects.filter( id=pk).first()
    #nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    #disciple = Discipline.objects.all()
    code = membre.groupetravail_id
    #TypeDoc = TypeDocument.objects.all()
    #DocClass = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id)  # Document à supprimer
    context = {
        'code': code,
        'membre': membre,
    }
    #groups.logo.delete(save=False)  # supprime le fichier du disque
    membre.delete()
    #return render(request, 'Documents/AjouterDocuments.html', context)
    messages.success(request, f"membre N°: {membre.Matricule_id} supprimé avec succès.")
    return redirect('AjouterFormGrpTrav',code)

#Dossier de Groupe de Travil
@login_required
def Ajouter_dossiersGrpTrav(request, pk):
    nomgroupe = get_object_or_404(GroupeTravails, id=pk)
    formateur = get_object_or_404(Formateurs, username_id=request.user.id)
    request.session['compte'] = formateur.Type
    nom_session = request.session.get('compte', 'Inconnu')

    ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=pk).order_by('-id')
    disciplines = Discipline.objects.all()
    niveaux = Niveau.objects.all()
    type_docs = TypeDocument.objects.all()

    if request.method == 'POST':
        form = DossiersGRPTravForm(request.POST, request.FILES)
        if form.is_valid():
            dossier = form.save(commit=False)
            dossier.groupetravail = nomgroupe
            dossier.username = request.user

            # Vérification (facultative) : discipline du groupe vs discipline du document
            if hasattr(nomgroupe, 'Discipline') and nomgroupe.Discipline != dossier.Discipline:
                messages.error(request, "Erreur : les disciplines sont différentes.")
                return redirect('Ajouter_dossiersGrpTrav', pk=pk)

            dossier.save()
            messages.success(request, "Document ajouté avec succès.")
            return redirect('Ajouter_dossiersGrpTrav', pk=pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

    else:
        form = DossiersGRPTravForm()

    context = {
        'pk': pk,
        'nomgroupe': nomgroupe,
        'form': form,
        'disciplines': disciplines,
        'niveaux': niveaux,
        'TypeDocs': type_docs,
        'ListeDossiers': ListeDossiers,
        'Types': nom_session,
    }
    return render(request, 'GroupeTravail/AjouterDossierGrpTrav.html', context)


# Dossiers Groupe Travail
@login_required
def Modifier_DossiersGrpTrav(request, pk):
    #Mesgroupes = DossiersGRPTrav.objects.filter(username_id=request.user.id)
    #Dossier =get_object_or_404( DossiersGRPTrav,id=pk)
    Dossier = DossiersGRPTrav.objects.filter(id=pk).first()
    ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=Dossier.groupetravail, username_id=request.user.id)
    nomgroupe = GroupeTravails.objects.filter(id=Dossier.groupetravail_id).first()

    form = DossiersGRPTravForm(instance=Dossier)
    if Dossier.Document:
        ancien_fichier = Dossier.Document.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'form': form,
        'username': get_object_or_404(Formateurs, username_id=request.user.id).username,
        'Dossier': Dossier,
        'ListeDossiers': ListeDossiers,
        'pk': pk,
        'nomgroupe':nomgroupe,
    }
    try:
        if request.method == 'POST':
            form = DossiersGRPTravForm(request.POST, request.FILES, instance=Dossier)
            # GroupeTravail = GroupeTravails(
            #   Groupe=request.POST.get("NomGroupe"),
            #   Responsable = request.POST.get("Responsable"),
            #   Contact = request.POST.get("Contact"),
            #   Discipline_id=request.POST.get("Discipline"),
            #   logo = request.FILES.get("logo"),
            #   CodeAffect = request.POST.get("CodeAffect"),
            #   username_id = request.user.id,
            # Supprimer l’ancien fichier si remplacé (dans la vue)
            if 'Document' in request.FILES and ancien_fichier:
                chemin_fichier = os.path.join(settings.MEDIA_ROOT, ancien_fichier)
                if os.path.isfile(chemin_fichier):
                    os.remove(chemin_fichier)

            # )

            if form.is_valid():
                form.save()
            else:
                #print(form.errors)  # Ajoute ceci pour voir les erreurs de validation
                messages.success(request, f"Document Groupe de travail: Modifié avec succès.")
            context = {
                "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
                'form': form,
                'username': get_object_or_404(Formateurs, username_id=request.user.id).username,
                'Dossier': Dossier,
                'ListeDossiers': ListeDossiers,
                'pk': pk,
                'nomgroupe': nomgroupe,
            }
    except IntegrityError:
        messages.success(request, "Erreur  !!!,Le code d'invitation est dèjà utilisé.")
        # return render(request, 'GroupeTravail/GroupeTravail.html', context)
    return render(request, 'GroupeTravail/ModifierDocumentsGrpTrav.html', context)

#Suppression document groupe de travail
@login_required
def Supp_DossiersGrpTrav(request, pk):
    Dossier = DossiersGRPTrav.objects.filter(id=pk).first()
    ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=Dossier.groupetravail, username_id=request.user.id)
    nomgroupe = GroupeTravails.objects.filter(id=Dossier.groupetravail_id).first()
    Docgroup = DossiersGRPTrav.objects.filter(Document=Dossier.Document)
    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        'username': get_object_or_404(Formateurs, username_id=request.user.id).username,
        'Dossier': Dossier,
        'ListeDossiers': ListeDossiers,
        'pk': pk,
        'nomgroupe': nomgroupe,
    }
    if  Docgroup.count()==1 :
        Dossier.Document.delete(save=False)  # supprime le fichier du disque
        Dossier.delete()
    else:
        Dossier.delete()

    messages.success(request, "Document Supprimer avec Succès.")
        # return render(request, 'GroupeTravail/GroupeTravail.html', context)
    #return render(request, 'GroupeTravail/ModifierDocumentsGrpTrav.html', context)
    return redirect('Ajouter_dossiersGrpTrav', Dossier.groupetravail_id)

@login_required
def ListeDocGRPTravPartType(request,pk,type_doc):
    nomgroup=GroupeTravails.objects.filter( id=pk).first()
    if request.method == 'POST':
        ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=pk,username_id=request.user.id,TypeDoc_id=type_doc,Niveau_id=request.POST.get("Niveau")).order_by('id')
        Class=request.POST.get("Niveau")
    else:
        ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=pk,username_id=request.user.id, TypeDoc_id=type_doc).order_by('id')
        Class=""

    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    # DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    form = DossiersGRPTravForm()
    context = {
            'pk': pk,
            'nomgroup': nomgroup,
            # 'form': form,
            'disciple': disciple,
            'niveau': niveau,
            # 'DocClass': DocClass
            'TypeDocs': TypeDocs,
            'ListeDossiers': ListeDossiers,
            'type_doc': type_doc,
            'Class':Class,
            'form':form,
        }
    return render(request, 'GroupeTravail/ListeDossierGrpTParType.html', context)

def Transfert_documentGrpTrav(request, pk): # MesDossiers vers DossiersGRPTrav
    doc = get_object_or_404(MesDossiers, pk=pk)
    #NivClasse = MaClasse.objects.get(id=doc.Niveau).Niveau
    #nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    FormClass = GroupeTravails.objects.filter(username_id=request.user.id,Discipline_id=doc.Discipline_id)  # Groupe Travail
    #print(FormClass)
    if doc.Document:
        ancien_fichier = doc.Document.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    if request.method == 'POST':
        #form = MesDocumentsForm(request.POST, request.FILES)
        #NivClasse = MaClasse.objects.get(id=request.POST["Groupe"])
        form  = DossiersGRPTrav(
            groupetravail=request.POST["Groupe"],
            Discipline_id=doc.Discipline,
            Niveau=doc.Niveau,
            TypeDoc=doc.TypeDoc,
            Titre=doc.Titre,
            Observation=doc.Observation,
            Etat=doc.Etat,
            Document=ancien_fichier,
            username_id=doc.username_id,

        )
        #if form.is_valid():

        form.save()
        messages.success(request, "Document Transferé avec succès.")
        #return redirect('Ajouter_dossiersGrpTrav',doc.groupetravail)
        return render(request, 'GroupeTravail/TransfertDocumentGrpTrav.html', {'form': form, 'doc': doc,
                                                                               'FormClass': FormClass
                                                                               })
    #else:
    form = DossiersGRPTravForm(instance=doc)
    return render(request, 'GroupeTravail/TransfertDocumentGrpEtude.html', {'form': form,'doc':doc,
                                                                'FormClass': FormClass
                                                                })

def CreerPartenariatGrpTrav(request,pk):
    #Liste des partenaires au Groupe demandeur ou Groupe partenaire
    # ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id,GroupeTravDemandeur_id=pk).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id,GroupeTravPartenaire_id =pk).order_by('id')
    MGroupeTravails =  get_object_or_404(GroupeTravails, id=pk)
    ListePartenariats = PartenariatGroupTrav.objects.filter(
        Q(ProfsDemandeur_id=request.user.id, GroupeTravDemandeur_id=pk) | Q(ProfsPartenaire_id=request.user.id,
                                                                             GroupeTravPartenaire_id=pk)).order_by('id')


    context = {
        "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
        #'form': form,
        #'MesClasses': MesClasses,
        'MGroupeTravails': MGroupeTravails,
        'ListePartenariats': ListePartenariats,
    }

    if request.method == 'POST':
        #Eviter les auto-parrainages
        MGroupe = GroupeTravails.objects.filter(CodeAffect=request.POST.get('CodeAffect')).first()

        if not  MGroupe:
            messages.success(request,
                             f"Le Code Groupe :{request.POST.get("CodeAffect")} n'existe pas  .")
            return render(request, 'Partenariat/CreerPartGrpTrav.html', context)

        if pk == MGroupe.id or MGroupe.username_id==request.user.id:
            messages.success(request,
                             f"Désolé !!!,On ne peut s'auto-Parrainer.")
            return render(request, 'Partenariat/CreerPartGrpTrav.html', context)
        try:
            #form = PartenariatClasseForm(request.POST)
            #MClassesChoix = get_object_or_404(MaClasse, id= request.POST.get("IDClasse"))
            if MGroupeTravails.Discipline!=  MGroupe.Discipline:
                messages.success(request,
                                 f"Niveau Classe :{MGroupeTravails.Discipline} non conforme au Niveau choisir:{ MGroupe.Discipline} .")
                return render(request, 'Partenariat/CreerPartGrpTrav.html', context)
            # print(request.POST.get("Discipline"))

            Partenaire = PartenariatGroupTrav(
                GroupeTravDemandeur_id=pk,
                ProfsDemandeur_id=request.user.id,
                GroupeTravPartenaire_id=MGroupe.id,
                ProfsPartenaire_id=MGroupe.username_id,
            )
            Partenaire.save()
            messages.success(request, "Partenariat crée avec Succès .")
            return redirect('CreerPartenariatGrpTrav',pk)
            #return render(request, 'Partenariat/CreerPartGrpTrav.html', context)
        except IntegrityError:
             messages.success(request, "Désolé !!!,Ce Partenariat existe déjà .")
    return render(request, 'Partenariat/CreerPartGrpTrav.html', context)

#Suppression partenariat Groupe Travail
def SuppPartenariatGrpTrav(request, pk):
    #Partenaire = PartenariatClasse.objects.get(id=pk)
    Partenaire=get_object_or_404(PartenariatGroupTrav, id=pk)
    ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id,
                                                            GroupeTravDemandeur_id=Partenaire.GroupeTravDemandeur)
    #ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id)
    if not ListePartenariats:
        #ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id)
        ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id,
                                                                GroupeTravPartenaire_id=Partenaire.GroupeTravPartenaire)
    #ListeClasse = MaClasse.objects.all()

    #Mclasse = ClasseForm(instance=Mclas)
    context = {
        'Partenaire': Partenaire,
        'ListePartenariats': ListePartenariats,
        #'MGroupeTravails': MGroupeTravails,
    }
    Partenaire.delete()
    messages.success(request, 'Partenariat supprimer avec Succès')
    return redirect('GroupeTrav')
    #return render(request, 'Partenariat/CreerPartGrpTrav.html', context)


def ListeDocumentPartGrpTrav(request,pk):
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    #ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id)
    #if not ListePartenariats:
     #   ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id)
    ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=pk).order_by('id')
    MesGroup = GroupeTravails.objects.filter(username_id=request.user.id)
    nomgroup = GroupeTravails.objects.get(id=pk)
    TypeDocs = TypeDocument.objects.all()
    context = {
        #'ListePartenariats': ListePartenariats,
        'nomgroup': nomgroup,
        'ListeDossiers':  ListeDossiers,
        'TypeDocs': TypeDocs,
        'pk': pk,
        "Types": nom_session,
        'MesGroup': MesGroup,
    }

    return render(request, 'Partenariat/ListeDocumentPartGrpTrav.html', context)

@login_required
def ListeDocGRPTravPartenTypeDoc(request,pk,type_doc):
    nomgroup=GroupeTravails.objects.filter( id=pk).first()
    if request.method == 'POST':
        ListeDossiers = DossiersGRPTrav.objects.filter(groupetravail_id=pk,TypeDoc_id=type_doc,Niveau_id=request.POST.get("Niveau")).order_by('id')
        Niv=request.POST.get("Niveau")
    else:
        ListeDossiers = DossiersGRPTrav.objects.filter( groupetravail=pk,TypeDoc=type_doc).order_by('id')

        Niv=""

    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    # DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    context = {
            'pk': pk,
            'nomgroup': nomgroup,
            # 'form': form,
            'disciple': disciple,
            'niveau': niveau,
            # 'DocClass': DocClass
            'TypeDocs': TypeDocs,
            'ListeDossiers': ListeDossiers,
            'type_doc': type_doc,
            'Niv':Niv,
        }
    #return render(request, 'GroupeTravail/ListeDossierGrpTParType.html', context)
    return render(request, 'Partenariat/ListeDocumentPartGrpTrav.html', context)

# Liste groupe de travail
def ListepartGrpTrav(request):
    request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # ListePartenariats=PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id).order_by('id')
    ListePartenariats = PartenariatGroupTrav.objects.filter(
        Q(ProfsDemandeur_id=request.user.id) | Q(ProfsPartenaire_id=request.user.id)
    ).order_by('id')

    ListeGrpTrav=GroupeTravails.objects.all()
    MesGrpTrav=GroupeTravails.objects.filter(username_id=request.user.id)
    MesTypes = TypeDocument.objects.all()
    Total=ListePartenariats.count()
    context={
        'ListePartenariats': ListePartenariats,
        'ListeGrpTrav':ListeGrpTrav,
        'MesTypes': MesTypes,
        'MesGrpTrav': MesGrpTrav,
        "Types": nom_session,
        'Total': Total,
    }
    return render(request,'Partenariat/ListePartGrpTrav.html',context)


# Groupe ETUDE

@login_required
def groupetude(request):

    form = GroupeEtudeForm()
    Nivo=Niveau.objects.all()
    # Mesgroupes = GroupeEtude.objects.filter(username_id=request.user.id).order_by('-id')
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    Mesgroupes = GroupeEtude.objects.filter(Q(id__in=MesGroupe.values_list('groupetude_id', flat=True)) | Q(username_id=request.user.id))
    paginator = Paginator(Mesgroupes, 10)  # 10 réunions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
         "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        'form': form,
        'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
        'Mesgroupes': page_obj,
        'Nivo': Nivo,
    }
    try:
        if request.method == 'POST':
            GroupeEtudes = GroupeEtude(
                Groupe=request.POST.get("NomGroupe"),
                Responsable=request.POST.get("Responsable"),
                Contact=request.POST.get("Contact"),
                Etablissement=request.POST.get("Etablissement"),
                Niveau_id =request.POST.get("Niveau"),
                logo=request.FILES.get("logo"),
                CodeAffect=request.POST.get("CodeAffect"),
                username_id=request.user.id,

            )
            GroupeEtudes.save()
            messages.success(request, "Groupe d'Etude crée avec succès.")
            context = {
                "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
                'form': form,
                'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
                'Mesgroupes': Mesgroupes,
                'Nivo': Nivo,
            }
    except IntegrityError:
        messages.success(request, "Désolé !!!,Le code d'invitation est dèjà utilisé.")
        # return render(request, 'GroupeTravail/GroupeTravail.html', context)
    return render(request, 'GroupeEtude/GroupEtude.html', context)

@login_required
def ModifGroupeEtude(request,pk):

    # Mesgroupes = GroupeEtude.objects.filter(username_id=request.user.id)
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
    MesGroupe = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)  # Selection de don Groupe
    # Selection des groupes parents
    #Mesgroupes = GroupeEtude.objects.filter(id__in=MesGroupe.values_list('groupetude_id', flat=True))
    Mesgroupes = GroupeEtude.objects.filter(
        Q(id__in=MesGroupe.values_list('groupetude_id', flat=True)) | Q(username_id=request.user.id))
    groups=GroupeEtude.objects.filter(id=pk).first()
    context = {
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        # 'form': form,
        'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
        'Mesgroupes': Mesgroupes,
        'groups': groups,
        'pk': pk,
    }
    if groups.username_id != request.user.id:
        messages.success(request, "Vous n'avez pas le droit de Modification")
        return render(request, 'GroupeEtude/ModifGroupeEtude.html',context)
    form=GroupeEtudeForm(instance=groups)

    if groups.logo:
        ancien_fichier = groups.logo.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    context = {
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        'form':form,
        'username':get_object_or_404(Apprenants, username_id=request.user.id).username,
        'Mesgroupes':Mesgroupes,
        'groups': groups,
        'pk':pk,
    }

    try:
        if request.method == 'POST':  # On verifie le code d'affectation

            if request.POST.get("CodeAffect")!=groups.CodeAffect:
                codeAff = GroupeEtude.objects.filter(CodeAffect=request.POST.get("CodeAffect"))
                if (codeAff and groups.pk != codeAff.pk):
                    messages.success(request, f"Ce Code {request.POST.get("CodeAffect")}: est déjà utilisé.")
                    return render(request, 'GroupeEtude/ModifGroupeEtude.html', context)
        if request.method == 'POST':
            form = GroupeEtudeForm(request.POST, request.FILES, instance=groups)
            if 'logo' in request.FILES and ancien_fichier:
                chemin_fichier = os.path.join(settings.MEDIA_ROOT, ancien_fichier)
                if os.path.isfile(chemin_fichier):
                    os.remove(chemin_fichier)

            #)
            form.save()
            messages.success(request, f"Groupe de travail: Modifié avec succès.")
            context = {
                "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
                'form': form,
                'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
                'Mesgroupes': Mesgroupes,
                'groups': groups,
                'pk': pk,
                }
    except IntegrityError:
        messages.success(request, "Désolé !!!,Le code d'invitation est dèjà utilisé.")
        #return render(request, 'GroupeTravail/GroupeTravail.html', context)

    return render(request, 'GroupeEtude/ModifGroupeEtude.html', context)

def Ajouter_dossiersGrpEtude(request,pk): # Selectionner un Groupe etude
    nomgroupe = GroupeEtude.objects.get(id=pk)
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    ListeDossiers=DossiersGRPEtude.objects.filter(groupetude_id=pk)
    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    #DocClass = MesDocuments.objects.filter(maclasse_id=pk)

    if request.method == 'POST':

        #if nomgroupe.Discipline!=request.POST.get("Discipline"):
         #   messages.success(request, "Erreur !!!,les Disciplines sont differentes.")
          #  return redirect('Ajouter_dossiersGrpTrav', pk)

        Dossiers = DossiersGRPEtude(
            groupetude_id=pk,
            Discipline_id=request.POST.get('discipline'),
            Niveau_id=request.POST.get("Niveau"),
            TypeDoc_id=request.POST.get("TypeDoc"),
            Titre=request.POST.get("Titre"),
            Observation=request.POST.get("Observation"),
            Etat=request.POST.get("Etat"),
            Document=request.FILES.get("document"),
            username_id=request.user.id,
            Dossier_link=request.POST.get("documenturl"),
        )

        Dossiers.save()
        context = {
            'pk': pk,
            'nomgroupe': nomgroupe,
            #'form': form,
            'disciple': disciple,
            'niveau': niveau,
            # 'DocClass': DocClass
            'TypeDocs': TypeDocs,
            'ListeDossiers': ListeDossiers,
            "Types": nom_session,
        }
        messages.success(request, "Document ajouté avec succès.")
        #return render(request, 'Documents/AjouterDossier.html', context)
        return redirect('Ajouter_dossiersGrpEtude', pk)
        #return render(request, 'GroupeTravail/AjouterDossierGrpTrav.html', context)

    else:
        form = GroupeEtudeForm()
        context = {
            'pk': pk,
            'nomgroupe': nomgroupe,
            'form': form,
            'disciple': disciple,
            'niveau': niveau,
            'TypeDocs': TypeDocs,
            # 'DocClass': DocClass
            'ListeDossiers': ListeDossiers,
            "Types": nom_session,
        }
        return render(request, 'GroupeEtude/AjouterDossierGrpEtude.html', context)

@login_required
def Modifier_DossiersGrpEtude(request, pk):
    #Mesgroupes = DossiersGRPTrav.objects.filter(username_id=request.user.id)
    #Dossier =get_object_or_404( DossiersGRPTrav,id=pk)
    Dossier = DossiersGRPEtude.objects.filter(id=pk).first()
    ListeDossiers = DossiersGRPEtude.objects.filter(groupetude_id=Dossier.groupetude, username_id=request.user.id)
    nomgroupe = GroupeEtude.objects.filter(id=Dossier.groupetude_id).first()

    form = DossiersGRPEtudeForm(instance=Dossier)
    if Dossier.Document:
        ancien_fichier = Dossier.Document.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    context = {
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        'form': form,
        'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
        'Dossier': Dossier,
        'ListeDossiers': ListeDossiers,
        'pk': pk,
        'nomgroupe':nomgroupe,
    }
    try:
        if request.method == 'POST':
            form = DossiersGRPEtudeForm(request.POST, request.FILES, instance=Dossier)

            if 'Document' in request.FILES and ancien_fichier:
                chemin_fichier = os.path.join(settings.MEDIA_ROOT, ancien_fichier)
                if os.path.isfile(chemin_fichier):
                    os.remove(chemin_fichier)

            # )

            if form.is_valid():
                form.save()
            else:
                #print(form.errors)  # Ajoute ceci pour voir les erreurs de validation
                messages.success(request, f"Document Groupe d'Etude: Modifié avec succès.")
            context = {
                "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
                'form': form,
                'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
                'Dossier': Dossier,
                'ListeDossiers': ListeDossiers,
                'pk': pk,
                'nomgroupe': nomgroupe,
            }
    except IntegrityError:
        messages.success(request, "Erreur  !!!,Le code d'invitation est dèjà utilisé.")
        # return render(request, 'GroupeTravail/GroupeTravail.html', context)
    return render(request, 'GroupeEtude/ModifierDocumentsGrpEtude.html', context)

def Supp_DossiersGrpEtude(request, pk):
    Dossier = DossiersGRPEtude.objects.filter(id=pk).first()
    ListeDossiers = DossiersGRPEtude.objects.filter(groupetude_id=Dossier.groupetude, username_id=request.user.id)
    nomgroupe = GroupeEtude.objects.filter(id=Dossier.groupetude_id).first()
    Docgroup =DossiersGRPEtude.objects.filter(Document=Dossier.Document)
    context = {
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        'username': get_object_or_404(Apprenants, username_id=request.user.id).username,
        'Dossier': Dossier,
        'ListeDossiers': ListeDossiers,
        'pk': pk,
        'nomgroupe': nomgroupe,
    }
    if  Docgroup.count()==1 :
        Dossier.Document.delete(save=False)  # supprime le fichier du disque
        Dossier.delete()
    else:
        Dossier.delete()

    messages.success(request, "Document Supprimer avec Succès.")
        # return render(request, 'GroupeTravail/GroupeTravail.html', context)
    #return render(request, 'GroupeTravail/ModifierDocumentsGrpTrav.html', context)
    return redirect('Ajouter_dossiersGrpEtude', Dossier.groupetude_id)

def SupGroupeEtude(request, pk):
    groups=GroupeEtude.objects.filter( id=pk).first()
    #nomclasse = MaClasse.objects.get(id=doc.maclasse_id)
    #disciple = Discipline.objects.all()
    #niveau = Niveau.objects.all()
    #TypeDoc = TypeDocument.objects.all()
    #DocClass = MesDocuments.objects.filter(maclasse_id=doc.maclasse_id)  # Document à supprimer
    context = {
        'pk': pk,

    }
    if groups.username_id != request.user.id:
        messages.success(request, "Vous n'avez pas le droit de Suppression")
        return redirect('groupetude')
    groups.logo.delete(save=False)  # supprime le fichier du disque
    groups.delete()
    #return render(request, 'Documents/AjouterDocuments.html', context)
    messages.success(request, f"Groupe N°: {pk} supprimé avec succès.")
    return redirect('groupetude')

@login_required
def AjouterApprenGrpEtude(request, pk):
    groupes = GroupeEtude.objects.filter(id=pk).first()
    total_groupe = Appren_GroupeEtude.objects.filter(groupetude=pk).count()
    Membregroupe = Appren_GroupeEtude.objects.filter(groupetude=pk)

    context = {
        'Membregroupe': Membregroupe,
        'groupes': groupes,
        'total_groupe': total_groupe,
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type
    }
    try:
        if request.method == 'POST':
            Format = Apprenants.objects.filter(Matricule=request.POST.get("Matricule")).exists()
            if not Format:
                messages.success(request, f"Matricule N°: {request.POST.get("Matricule")} n'existe pas.")
                return render(request, 'GroupeEtude/AjouterAppGrpEtude.html', context)
            else:

               form = Appren_GroupeEtude(
                   Matricule_id=request.POST.get("Matricule"),
                   groupetude_id=pk,
               )
            form.save()
            context = {
                'Membregroupe': Membregroupe,
                'groupes': groupes,
                'total_groupe': Appren_GroupeEtude.objects.filter(groupetude=pk).count(),
                "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type
            }
            messages.success(request, f"Matricule N°: {request.POST.get("Matricule")} ajouté avec succès.")
            #return render(request, 'GroupeTravail/AjouterFormGrpTrav.html', context)
    except IntegrityError:
            messages.success(request, f"Matricule N°: {request.POST.get("Matricule")} existe déjà dans le Groupe.")
    return render(request, 'GroupeEtude/AjouterAppGrpEtude.html', context)

@login_required
def SupMembreGroupeEtude(request, pk):
    membre=Appren_GroupeEtude.objects.filter( id=pk).first()
    code = membre.groupetude_id
    context = {
        'code': code,
        'membre': membre,
    }
    #groups.logo.delete(save=False)  # supprime le fichier du disque
    membre.delete()
    #return render(request, 'Documents/AjouterDocuments.html', context)
    messages.success(request, f"membre N°: {membre.Matricule_id} supprimé avec succès.")
    return redirect('AjouterApprenGrpEtude',code)

def CreerPartenariatGrpEtude(request,pk):
    #Liste des partenaires au Groupe demandeur ou Groupe partenaire
    # ListePartenariats = PartenariatGroupEtude.objects.filter(ApprenDemandeur_id=request.user.id,GroupeEtudDemandeur_id=pk).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatGroupTrav.objects.filter(ApprenPartenaire_id=request.user.id,GroupeEtudPartenaire_id =pk).order_by('id')
    MGroupeEtude =  get_object_or_404(GroupeEtude, id=pk)

    # ListePartenariats=PartenariatGroupEtude.objects.filter(Q(ApprenDemandeur_id=request.user.id,GroupeEtudDemandeur_id=pk) |
    #                 Q(ApprenPartenaire_id=request.user.id,GroupeEtudPartenaire_id =pk)).order_by('id')

    ListePartenariats = PartenariatGroupEtude.objects.filter(
        Q(GroupeEtudDemandeur_id=pk) | Q(GroupeEtudPartenaire_id=pk)).order_by('id')
    #MesClasses = MaClasse.objects.all()

    context = {
        "Types": get_object_or_404(Apprenants, username_id=request.user.id).Type,
        #'form': form,
        #'MesClasses': MesClasses,
        'MGroupeEtude': MGroupeEtude,
        'ListePartenariats': ListePartenariats,
        'pk':pk
    }

    if request.method == 'POST':
        #Eviter les auto-parrainages
        MGroupe = GroupeEtude.objects.filter(CodeAffect=request.POST.get('CodeAffect')).first()

        if not  MGroupe:
            messages.success(request,
                             f"Le Code Groupe :{request.POST.get("CodeAffect")} n'existe pas  .")
            return render(request, 'Partenariat/CreerPartGrpEtude.html', context)

        if pk == MGroupe.id or MGroupe.username_id==request.user.id:
            messages.success(request,
                             f"Désolé !!!,On ne peut s'auto-Parrainer.")
            return render(request, 'Partenariat/CreerPartGrpEtude.html', context)
        try:
            #form = PartenariatClasseForm(request.POST)
            #MClassesChoix = get_object_or_404(MaClasse, id= request.POST.get("IDClasse"))
            if MGroupeEtude.Niveau !=  MGroupe.Niveau:
                messages.success(request,
                                 f"Niveau Groupe :{MGroupeEtude.Niveau} non conforme au Niveau choisir:{ MGroupe.Niveau} .")
                return render(request, 'Partenariat/CreerPartGrpEtude.html', context)
            # print(request.POST.get("Discipline"))

            Partenaire = PartenariatGroupEtude(
                GroupeEtudDemandeur_id=pk,
                ApprenDemandeur_id =request.user.id,
                GroupeEtudPartenaire_id=MGroupe.id,
                ApprenPartenaire_id =MGroupe.username_id,
                Auteur_id=request.user.id,
            )
            Partenaire.save()
            messages.success(request, "Partenariat crée avec Succès .")
            return redirect('CreerPartenariatGrpEtude',pk)
            #return render(request, 'Partenariat/CreerPartGrpTrav.html', context)
        except IntegrityError:
             messages.success(request, "Désolé !!!,Ce Partenariat existe déjà .")
    return render(request, 'Partenariat/CreerPartGrpEtude.html', context)

def ListeDocumentPartGrpEtude(request,pk):
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    #ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id)
    #if not ListePartenariats:
     #   ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id)
    ListeDossiers = DossiersGRPEtude.objects.filter(groupetude_id=pk).order_by('id')
    MesGroup = GroupeEtude.objects.filter(username_id=request.user.id)
    nomgroup = GroupeEtude.objects.get(id=pk)
    TypeDocs = TypeDocument.objects.all()
    context = {
        #'ListePartenariats': ListePartenariats,
        'nomgroup': nomgroup,
        'ListeDossiers':  ListeDossiers,
        'TypeDocs': TypeDocs,
        'pk': pk,
        "Types": nom_session,
        'MesGroup': MesGroup,
    }

    return render(request, 'Partenariat/ListeDocumentPartGrpEtude.html', context)

def SuppPartenariatGrpEtude(request, pk):
    #Partenaire = PartenariatClasse.objects.get(id=pk)
    Partenaire=get_object_or_404(PartenariatGroupEtude, id=pk)
    # ListePartenariats = PartenariatGroupEtude.objects.filter(ProfsDemandeur_id=request.user.id,
    #                                                         GroupeTravDemandeur_id=Partenaire.GroupeTravDemandeur)
    # #ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id)
    # if not ListePartenariats:
    #     #ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id)
    #     ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id,
    #                                                             GroupeTravPartenaire_id=Partenaire.GroupeTravPartenaire)
    ListePartenariats = PartenariatGroupEtude.objects.filter(
        Q(ApprenDemandeur_id=request.user.id, GroupeEtudDemandeur_id=pk) | Q(ApprenPartenaire_id=request.user.id,
                                                                             GroupeEtudPartenaire_id=pk)).order_by('id')
    #ListeClasse = MaClasse.objects.all()

    #Mclasse = ClasseForm(instance=Mclas)
    context = {
        'Partenaire': Partenaire,
        'ListePartenariats': ListePartenariats,
        #'MGroupeTravails': MGroupeTravails,
    }
    if Partenaire.Auteur_id == request.user.id:
        Partenaire.delete()
        messages.success(request, 'Partenariat supprimer avec Succès')
        return redirect('groupetude')

    messages.success(request, 'Impossible de supprimer ce Partenariat')
    return redirect('groupetude')
    #return render(request, 'Partenariat/CreerPartGrpTrav.html', context)

def ListeDocGRPEtudePartenTypeDoc(request,pk,type_doc):
    nomgroup=GroupeEtude.objects.filter( id=pk).first()
    if request.method == 'POST':
        ListeDossiers = DossiersGRPEtude.objects.filter(groupetude_id=pk,TypeDoc_id=type_doc,Niveau_id=request.POST.get("Niveau")).order_by('-id')
        Niv=request.POST.get("Niveau")
    else:
        ListeDossiers = DossiersGRPEtude.objects.filter( groupetude_id=pk,TypeDoc=type_doc).order_by('-id')

        Niv=""

    disciple = Discipline.objects.all()
    niveau = Niveau.objects.all()
    TypeDocs = TypeDocument.objects.all()
    # DocClass = MesDocuments.objects.filter(maclasse_id=pk)
    context = {
            'pk': pk,
            'nomgroup': nomgroup,
            # 'form': form,
            'disciple': disciple,
            'niveau': niveau,
            # 'DocClass': DocClass
            'TypeDocs': TypeDocs,
            'ListeDossiers': ListeDossiers,
            'type_doc': type_doc,
            'Niv':Niv,
        }
    #return render(request, 'GroupeTravail/ListeDossierGrpTParType.html', context)
    return render(request, 'Partenariat/ListeDocumentPartGrpEtude.html', context)

def ListepartGrpEtude(request):
    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    # ListePartenariats=PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id).order_by('id')
    # if not ListePartenariats:
    #     ListePartenariats = PartenariatGroupTrav.objects.filter(ProfsPartenaire_id=request.user.id).order_by('id')
    ListePartenariats = PartenariatGroupEtude.objects.filter(
        Q(ApprenDemandeur_id=request.user.id) | Q(ApprenPartenaire_id=request.user.id)
    ).order_by('-id')

    ListeGrpTrav=GroupeEtude.objects.all()
    MesGrpTrav=GroupeEtude.objects.filter(username_id=request.user.id)
    MesTypes = TypeDocument.objects.all()
    Total=ListePartenariats.count()
    context={
        'ListePartenariats': ListePartenariats,
        'ListeGrpTrav':ListeGrpTrav,
        'MesTypes': MesTypes,
        'MesGrpTrav': MesGrpTrav,
        "Types": nom_session,
        'Total': Total,
    }
    return render(request,'Partenariat/ListePartGrpEtude.html',context)

def Transfert_documentGrpEtude(request, pk): # Transferer de Mesdossier vers Dossier Groupe Travail
    doc = get_object_or_404(MesDossiers, pk=pk)
    # FormClass = GroupeEtude.objects.filter(username_id=request.user.id,Niveau=doc.Niveau_id)  # Groupe Travail
    GroupeEt = GroupeEtude.objects.filter(username_id=request.user.id, Niveau=doc.Niveau)  # Mes Groupe etude

    if doc.Document:
        ancien_fichier = doc.Document.name  # chemin relatif vers MEDIA
    else:
        ancien_fichier = None

    if request.method == 'POST':
        form  = DossiersGRPEtude(
            groupetude_id=request.POST.get('Groupe'),
            Discipline_id=doc.Discipline,
            Niveau=doc.Niveau,
            TypeDoc=doc.TypeDoc,
            Titre=doc.Titre,
            Observation=doc.Observation,
            Etat=doc.Etat,
            Document=ancien_fichier,
            Dossier_link=doc.Dossier_link,
            username_id=doc.username_id,

        )
        #if form.is_valid():

        form.save()
        ListeDossiers = DossiersGRPEtude.objects.filter(groupetude_id=request.POST.get('Groupe'))
        #print(ListeDossiers.values())
        context = {
            'form': form,
            'doc': doc,
            'GroupeEt': GroupeEt,
            'ListeDossiers':ListeDossiers,
            'GroupeEtude':GroupeEtude.objects.filter(id=request.POST.get('Groupe')).first(),
        }

        messages.success(request, "Document Transferé avec succès.")
        #return redirect('Ajouter_dossiersGrpTrav',doc.groupetravail)
        return render(request, 'GroupeEtude/TransfertDocumentGrpEtude.html', context)
    #else:

    form = DossiersGRPTravForm()
    return render(request, 'GroupeEtude/TransfertDocumentGrpEtude.html', {'form': form,'doc':doc,
                                                                'GroupeEt': GroupeEt
                                                                })

#======MON ESPACE
@login_required
def monespace(request): # Espace Formateur

    if request.user.is_authenticated:

        "Rechercher un utilisateur."
        Appren = Apprenants.objects.filter(username_id=request.user.id).first()
        Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

        if not Appren and not Forma :
            return render(request, 'registration/Profil.html', {})

        if Appren:
            # Activation du compte
            DelaisAppren = Apprenants.objects.filter(username_id=request.user.id, actif=True).first()
            if not DelaisAppren :
                return render(request, 'registration/DelaisProfil.html', {})

            #Calcul des delai:
            # Delais=Apprenants.objects.filter(Q(username_id=request.user.id),Q(DateDuJour__lt=timezone.now())).first()
            # if Delais:
            #     # Delais.DateDuJour=datetime.now()
            #     jour = timezone.now() - Delais.create_at
            #     # Delais.Delai=Delais.Delai-1
            #     # Delais.save()
            #     # print(Delais)
            #     print(jour.days)
            Delais = Apprenants.objects.filter(
                Q(username_id=request.user.id),
                Q(DateDuJour__lt=timezone.now())
            ).first()
            user=User.objects.get(id=request.user.id)
            if Delais and Delais.create_at:
                difference = timezone.now() - Delais.create_at
                Marge=Delais.Delai -difference.days
                if Marge >=0 :
                    Delais.Delai = Marge
                else :
                    Delais.Delai = 0
                    Delais.actif=0
                    # user.is_active = False
                Delais.DateDuJour = timezone.now()
                Delais.save()



            reunions_list = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion encours
            # Toutes les classes de l'apprenant
            Part = PartenariatClasse.objects.all()
            MesCla=apprenant_maclasses.objects.filter(apprenant_id= Appren.Matricule)
            MesClasses = MaClasse.objects.filter(id__in=MesCla.values_list('maclasse_id'))
            # Pagination sur mesclasse
            paginator_mesclasse = Paginator(MesClasses, 10)  # 10 éléments par page
            page_num_mesclasse = request.GET.get('page_classe')
            page_mesclasse = paginator_mesclasse.get_page(page_num_mesclasse)

            MesClas=MaClasse.objects.filter(Q(id__in= MesCla.values_list('maclasse_id')),
            Q(id__in=Part.values_list('ClassDemandeur_id', flat=True)) | Q(id__in=Part.values_list('ClassPartenaire_id', flat=True)))


            # les classes objet de reunion                                            )
            mesreunions = Reunion.objects.filter(maclasse_id__in=MesCla.values_list('maclasse_id', flat=True),etat=0)
            # Les classes ayant fait objet de reunion
            mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))
            request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            #======================Liste des Reunion groupe Etude========================
            reunions_listEtude = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion encours
            # Toutes les classes de l'apprenant
            MesGroupeEtud = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)
            MesGroupeEtude = GroupeEtude.objects.filter(Q(id__in= MesGroupeEtud.values_list('groupetude_id', flat=True)) |
                                                                  Q(username_id=request.user.id))
            # les  reunions                                            )
            mesreunionsEtudes = ReunionEtude.objects.filter(groupeetude_id__in=MesGroupeEtude.values_list('id', flat=True), etat=0)
            #print(mesreunionsEtudes.values())
            # Les Groupes ayant fait objet de reunion
            MesGroupes = GroupeEtude.objects.filter(id__in=mesreunionsEtudes.values_list('groupeetude_id', flat=True))

            #======================CLASSE PARTENAIRE=======================
            # Part=PartenariatClasse.objects.all()
            # MesClas1=MaClasse.objects.filter(Q(id__in= MesClas.values_list('id')), Q(id__in=Part.values_list('ClassDemandeur_id', flat=True)) |
            #     Q(id__in=Part.values_list('ClassPartenaire_id', flat=True)))
            # print(MesClas1.values())
            ListePartenariats = PartenariatClasse.objects.filter(
                Q(ClassDemandeur_id__in=MesClas.values_list('id', flat=True)) |
                Q(ClassPartenaire_id__in=MesClas.values_list('id', flat=True)))

            # ======================DOCUMENTS CLASSE=======================
            DocClass = MesDocuments.objects.filter(maclasse_id__in=MesClas.values_list('id', flat=True))
            # Pagination sur DocClasse
            paginator_DocClass = Paginator(DocClass, 10)  # 10 éléments par page
            page_num_DocClass = request.GET.get('page_DocClass')
            page_DocClass = paginator_DocClass.get_page(page_num_DocClass)

            ClassDoc=MaClasse.objects.filter(id__in=DocClass.values_list('maclasse_id', flat=True))
            Mongroupe = GroupeEtude.objects.filter(username_id=request.user.id)
            DocGrpEtude = DossiersGRPEtude.objects.filter(username_id=request.user.id)

            # ======================DOCUMENTS Public=======================

            DocPublic = MesDocuments.objects.filter(Etat="PUBLIC",Niveau=Appren.Niveau).order_by('TypeDoc')
            # Pagination sur DocClasse
            paginator_DocPublic = Paginator(DocPublic, 10)  # 10 éléments par page
            page_num_DocPublic = request.GET.get('page_DocPublic')
            page_DocPublic = paginator_DocPublic.get_page(page_num_DocPublic)
                # Selectionnez les disciplines qui ont une matiere
            Disciplines=Discipline.objects.filter(discipline__in=DocPublic.values_list('Discipline_id',flat=True))
            

            # ======================MES REUNIONS CLASSE PARTENAIRE=======================
            mesreunionPart = Reunion.objects.filter(Q(maclasse_id__in=ListePartenariats.values_list('ClassDemandeur_id', flat=True)) |
                                                    Q(maclasse_id__in=ListePartenariats.values_list('ClassPartenaire_id', flat=True)),etat=0)

            # Mes Partenaires ayant une reunion encours
            mesreunionParts=mesreunionPart.filter(~Q(maclasse_id__in=MesClas.values_list('id', flat=True)) |
                                                  ~Q(maclasse_id__in=MesClas.values_list('id', flat=True)))
            mesclasseP = MaClasse.objects.filter(id__in= mesreunionParts.values_list('maclasse_id', flat=True))

            # =====Mes groupe de Etude====================
            Appren = Apprenants.objects.filter(username_id=request.user.id).first()  # Choix de l'apprenant
            MesGroupe = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule) # Voir s'il appartient à un groupe
            # MesgroupeDem=[]
            if not MesGroupe: # groupe vide et ayant un Groupe etude
                Mesgroupes=GroupeEtude.objects.filter(username_id=request.user.id)
                # Pagination sur Mesgroupe
                paginator_Mesgroupes = Paginator(Mesgroupes, 10)  # 10 éléments par page
                page_num_Mesgroupes = request.GET.get('page_Mesgroupes')
                page_Mesgroupes = paginator_Mesgroupes.get_page(page_num_Mesgroupes)

                MesgroupeDem = GroupeEtude.objects.filter(username_id=request.user.id).first() #Ayant un groupe
                # Mesgroupes = GroupeEtude.objects.filter(
                #     Q(username_id=request.user.id) | Q(id__in=MesGroupe.values_list('id', flat=True)))
                ListePartenariatsGrps = PartenariatGroupEtude.objects.filter(
                    Q(GroupeEtudDemandeur_id__in=Mesgroupes.values_list('id', flat=True)) |
                    Q(GroupeEtudPartenaire_id__in=Mesgroupes.values_list('id', flat=True))
                )
                ListePartenariatsGrp = GroupeEtude.objects.filter(
                    Q(id__in=ListePartenariatsGrps.values_list('GroupeEtudDemandeur_id', flat=True)) |
                    Q(id__in=ListePartenariatsGrps.values_list('GroupeEtudPartenaire_id', flat=True)))

                # Selection des groupes parents

            if MesGroupe: # Invité non vide et n'ayant pas de Groupe
                Mesgroupes = GroupeEtude.objects.filter(
                Q(username_id=request.user.id) | Q(id__in=MesGroupe.values_list('groupetude_id', flat=True)))
                MesgroupeDem = GroupeEtude.objects.filter(username_id=request.user.id) # Pas de groupe

                #Selection des partenaires
                ListePartenariatsGrps = PartenariatGroupEtude.objects.filter(
                Q(GroupeEtudDemandeur_id__in=Mesgroupes.values_list('id', flat=True)) |
                    Q(GroupeEtudPartenaire_id__in=Mesgroupes.values_list('id', flat=True)))
                ListePartenariatsGrp = GroupeEtude.objects.filter(Q(id__in=ListePartenariatsGrps.values_list('GroupeEtudDemandeur_id', flat=True)) |
                    Q(id__in=ListePartenariatsGrps.values_list('GroupeEtudPartenaire_id', flat=True)))
            #======================Partenariat==============================
            # Toutes les Groupe etude de l'apprenant
            #MesGroupeEtud = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)
            #
            # print("+" * 100)
            # print(MesGroupe.values())

            context = {
                'MesClas': MesClas,
                'Mongroupe':Mongroupe,
                'TotalClasse': MaClasse.objects.filter(username_id=request.user.id).count(),
                # "Types": request.session['compte'],
                'MesGroupes': MesGroupes,
                'mesreunionsEtudes':mesreunionsEtudes,
                # 'ClassePart': ClassePart,
                'DocClass': page_DocClass,
                'ClassDoc':ClassDoc,
                # 'MonGrpInvites': MonGrpInvites,
                'ListePartenariats': ListePartenariats,
                'ListePartenariatsGrp': ListePartenariatsGrp,
                'MesgroupeDem': MesgroupeDem,
                'Mesgroupes':  page_Mesgroupes,
                'MesGroupe':MesGroupe,
                'mesclasse': page_mesclasse,
                'mesreunions': mesreunions,
                'reunions_list': reunions_list,
                'mesreunionParts':mesreunionParts,
                'mesclasseP':mesclasseP,
                'DocGrpEtude':DocGrpEtude,
                'DocPublic':page_DocPublic,
                'Disciplines':Disciplines,
                'Appren':Appren,
                'MesClasses':MesClasses,
            }
            return render(request, 'MonEspaceAp.html',context)

        if Forma:
                reunions_list = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion de classe
                mesreunions = Reunion.objects.filter(formateurs_id=request.user.id,
                                                     etat=0)  # Toutes les reunions de l'utilisateur
                #--------------Les classes du formateur----------
                MesClasses=MaClasse.objects.filter(username_id=request.user.id)

                # Les classes ayant fait objet de reunion
                mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))
                # request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type

                #=====Mes groupe de travails=======
                formas = Formateurs.objects.filter(username_id=request.user.id).first()  # Choix du Formateurs
                MesGroupe = form_grpe_travails.objects.filter(Matricule_id=formas.Matricule)  # Selection de membre Groupe
                # Selection des groupes parents
                Mesgroupes = GroupeTravails.objects.filter(
                    Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)))

                # =====Mes Documents groupe de travails=======
                DocClass = MesDocuments.objects.filter(username_id=request.user.id)
                code=Formateurs.objects.filter(username_id=request.user.id).first()
                MonGrpInvites=form_grpe_travails.objects.filter(Matricule_id=code.Matricule)

                ListePartenariats = PartenariatClasse.objects.filter(
                    Q(ProfDemandeur_id=request.user.id) | Q(ProfPartenaire_id=request.user.id)
                ).order_by('id')

                #Les Classes objets de partenariat
                MesClasPart = MaClasse.objects.filter(Q(username_id=request.user.id),
                    Q(id__in=ListePartenariats.values_list('ClassDemandeur_id', flat=True)) |
                    Q(id__in=ListePartenariats.values_list('ClassPartenaire_id', flat=True)))

                # MesClassePart = MaClasse.objects.filter(
                #          Q(id__in=ListePartenariats.values_list('ClassDemandeur_id', flat=True)) |
                #          Q(id__in=ListePartenariats.values_list('ClassPartenaire_id', flat=True))).distinct()
                # ListePartenariats = PartenariatClasse.objects.filter(ProfDemandeur_id=request.user.id)
                # if not ListePartenariats:
                #     ListePartenariats = PartenariatClasse.objects.filter(ProfPartenaire_id=request.user.id)
                #
                # ListePartenariatsGrp = PartenariatGroupTrav.objects.filter(ProfsDemandeur_id=request.user.id).order_by(
                #     'id')
                # if not ListePartenariatsGrp:
                #     ListePartenariatsGrp = PartenariatGroupTrav.objects.filter(
                #         ProfsPartenaire_id=request.user.id).order_by('id')
                # =============Partenaire de Groupe de travail===============
                ListePartenariatsGrp = PartenariatGroupTrav.objects.filter(
                    Q(ProfsDemandeur_id=request.user.id) | Q(ProfsPartenaire_id=request.user.id)
                ).order_by('id')

                # Les Groupe objets de partenariat
                MesGrpPart = GroupeTravails.objects.filter(Q(username_id=request.user.id),
                                                      Q(id__in=ListePartenariatsGrp.values_list('GroupeTravDemandeur_id',
                                                                                             flat=True)) |
                                                      Q(id__in=ListePartenariatsGrp.values_list('GroupeTravPartenaire_id',
                                                                                             flat=True)))

                nom_session = request.session.get('compte', 'Inconnu')
                Mongroupe= GroupeTravails.objects.filter(username_id=request.user.id)
                DocGrpTrav = DossiersGRPTrav.objects.filter(username_id=request.user.id)
                MesClas = MaClasse.objects.filter(id__in=DocClass.values_list('maclasse_id', flat=True))
                #MesClas=MaClasse.objects.filter(username_id=request.user.id).order_by('id'),


                #=============Reunion de Groupe de travail===============
                forma = Formateurs.objects.filter(username_id=request.user.id).first()
                MesGroupe = form_grpe_travails.objects.filter(Matricule=forma.Matricule)
                mesGroupeTrav = GroupeTravails.objects.filter(
                    Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
                # mesreunions = ReunionGrpTravail.objects.filter(formateurs_id=request.user.id) # Toutes les reunions de l'utilisateur
                # Les groupes ayant fait objet de reunion

                reunions_listGrpT = ReunionGrpTravail.objects.filter(Q(etat=0),
                    Q(groupetravail_id__in=mesGroupeTrav.values_list('id', flat=True))).order_by('-id')
                context = {
                    'MesClas': MesClas,
                    'TotalClasse': MaClasse.objects.filter(username_id=request.user.id).count(),
                    # "Types": get_object_or_404(Formateurs, username_id=request.user.id).Type,
                    'Mesgroupes': Mesgroupes,
                    'DocClass': DocClass,
                    'MesGrpPart': MesGrpPart,
                    'ListePartenariats': ListePartenariats,
                    'ListePartenariatsGrp': ListePartenariatsGrp,
                    'DocGrpTrav': DocGrpTrav,
                    'Mongroupe': Mongroupe,
                    'mesclasse':mesclasse,
                    'MesClasses': MesClasses,
                    'mesreunions':mesreunions,
                    'reunions_list':reunions_list,
                    'reunions_listGrpT': reunions_listGrpT,
                    'mesGroupeTrav':mesGroupeTrav,
                    'MesClasPart': MesClasPart,
                    'forma':forma,
                }
                return render(request, 'MonEspace.html', context)

def monespaceVideo(request): # Espace Formateur

    if request.user.is_authenticated:

        "Rechercher un utilisateur."
        Appren = Apprenants.objects.filter(username_id=request.user.id).first()
        Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

        if not Appren and not Forma :
            return render(request, 'registration/Profil.html', {})

        if Appren:
            reunions_list = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion encours
            # Toutes les classes de l'apprenant
            MesCla=apprenant_maclasses.objects.filter(apprenant_id= Appren.Matricule)
            MesClas=MaClasse.objects.filter(id__in= MesCla.values_list('maclasse_id'))
            # les classes objet de reunion                                            )
            mesreunions = Reunion.objects.filter(maclasse_id__in=MesCla.values_list('maclasse_id', flat=True),etat=0)
            # Les classes ayant fait objet de reunion
            mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))
            request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
            nom_session = request.session.get('compte', 'Inconnu')
            #======================Liste des Reunion groupe Etude========================
            reunions_listEtudes = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion encours
            # Toutes les Groupe etude de l'apprenant
            MesGroupeEtud = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)

            MesGroupeEtude = GroupeEtude.objects.filter(
                Q(id__in=MesGroupeEtud.values_list('groupetude_id', flat=True)) |
                Q(username_id=request.user.id))

            #print(MesGroupeEtude.values())
            # les  reunions                                            )
            mesreunionsEtudes = ReunionEtude.objects.filter(
                groupeetude_id__in=MesGroupeEtude.values_list('id', flat=True), etat=0)

            #print(mesreunionsEtudes.values())
            # Les Groupes ayant fait objet de reunion
            MesGroupes = GroupeEtude.objects.filter(id__in=mesreunionsEtudes.values_list('groupeetude_id', flat=True))

            #====================
            MreunionsEtudes = ReunionEtude.objects.filter(
                groupeetude_id__in=MesGroupeEtude.values_list('id', flat=True), etat=1)
            # print(mesreunionsEtudes.values())
            # Les Groupes ayant fait objet de reunion
            MesGroupeEtude = GroupeEtude.objects.filter(id__in=MreunionsEtudes.values_list('groupeetude_id', flat=True))
            print(MesGroupeEtude.values())

            context = {
                'MesClas': MesClas,
                'TotalClasse': MaClasse.objects.filter(username_id=request.user.id).count(),
                "Types": request.session['compte'],
                'MesGroupes': MesGroupes,
                'mesreunionsEtudes':mesreunionsEtudes,
                'mesclasse': mesclasse,
                'mesreunions': mesreunions,
                'reunions_list': reunions_list,
                'MesGroupeEtude':MesGroupeEtude,
                'MreunionsEtudes': MreunionsEtudes,
            }
            return render(request, 'CoursVideoAnterieurs/EspaceVideoAnterieurAp.html', context)

        if Forma:
                reunions_list = Reunion.objects.filter(etat=1).order_by("-id")  # Toutes les reunion de classe
                mesreunions = Reunion.objects.filter(formateurs_id=request.user.id,
                                                     etat=1)  # Toutes les reunions de l'utilisateur
                #--------------Les classes du formateur----------
                MesClasses=MaClasse.objects.filter(username_id=request.user.id)

                # Les classes ayant fait objet de reunion
                mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))
                request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type


                # #=============Reunion de Groupe de travail===============
                forma = Formateurs.objects.filter(username_id=request.user.id).first()
                MesGroupe = form_grpe_travails.objects.filter(Matricule=forma.Matricule)
                mesGroupeTrav = GroupeTravails.objects.filter(
                    Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
                # # mesreunions = ReunionGrpTravail.objects.filter(formateurs_id=request.user.id) # Toutes les reunions de l'utilisateur
                # # Les groupes ayant fait objet de reunion

                reunions_listGrpT = ReunionGrpTravail.objects.filter(Q(etat=1),
                    Q(groupetravail_id__in=mesGroupeTrav.values_list('id', flat=True))).order_by('-id')

                context = {
                    # 'MesClas': MesClas,
                    'TotalClasse': MaClasse.objects.filter(username_id=request.user.id).count(),
                    'Types': get_object_or_404(Formateurs, username_id=request.user.id).Type,
                    # 'Mesgroupes': Mesgroupes,
                    # 'DocClass': DocClass,
                    # 'MesGrpPart': MesGrpPart,
                    # 'ListePartenariats': ListePartenariats,
                    # 'ListePartenariatsGrp': ListePartenariatsGrp,
                    # 'DocGrpTrav': DocGrpTrav,
                    # 'Mongroupe': Mongroupe,
                    'mesclasse':mesclasse,
                    'MesClasses': MesClasses,
                    'mesreunions':mesreunions,
                    'reunions_list':reunions_list,
                    'reunions_listGrpT': reunions_listGrpT,
                    'mesGroupeTrav':mesGroupeTrav,
                    # 'MesClasPart': MesClasPart,
                }
                return render(request, 'CoursVideoAnterieurs/EspaceVideoAnterieur.html',context)


#----------COURS A DOMICILE-------------



# def forums(request):
#     Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
#     Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
#
#     if not (Appren or Forma):  # non existant
#         return render(request, 'CoursDom.html')
#     else:  # si existant
#         if Forma:
#             request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
#             nom_session = request.session.get('compte', 'Inconnu')
#             context = {
#                 "Types": nom_session,
#             }
#             return render(request, 'CoursDom.html',context)
#
#         if Appren:
#             request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
#             nom_session = request.session.get('compte', 'Inconnu')
#             context = {
#                 "Types": nom_session,
#             }

# @login_required
# def forums(request):
#     Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
#     Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
#
#     if not (Appren or Forma):  # non existant
#         return render(request, 'CoursDom.html')
#     else:  # si existant
#         if Forma:
#             request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
#             nom_session = request.session.get('compte', 'Inconnu')
#             context = {
#                 "Types": nom_session,
#             }
#             return render(request, 'CoursDom.html',context)
#
#         if Appren:
#             request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
#             nom_session = request.session.get('compte', 'Inconnu')
#             context = {
#                 "Types": nom_session,
#             }

# Forum
@login_required
def nouveau_sujet(request):
    sujets = SujetDiscussion.objects.all().order_by('-date_creation')
    nom_session = request.session.get('compte', 'Inconnu')
    # Selection du menu selon le type
    base_template = ""
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"

    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
    else :
        base_template = "Menus/Menu.html"

    if request.method == 'POST':
        form = SujetForm(request.POST)
        if form.is_valid():
            sujet = form.save(commit=False)
            sujet.auteur = request.user
            sujet.save()
            return redirect('forum')
    else:
        form = SujetForm()
    context = {
        'base_template': base_template,
        'Types': nom_session,
        'form': form
    }
    return render(request, 'Forum/nouveau_sujet.html', context)

@login_required
def detail_sujet(request, pk):
    sujets = SujetDiscussion.objects.all().order_by('-date_creation')
    nom_session = request.session.get('compte', 'Inconnu')
    # Selection du menu selon le type
    base_template = ""
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"

    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
        Appren=Apprenants.objects.get(username_id=request.user.id)
    else:
        base_template= "Menus/Menu.html"
    context = {
        'sujets': sujets,
        'base_template': base_template,
        'Types': nom_session,

    }
    sujet = get_object_or_404(SujetDiscussion, pk=pk)
    mess = sujet.messages.all()
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sujet = sujet
            message.auteur = request.user
            message.save()
            return redirect('detail_sujet', pk=sujet.pk)
    else:
        form = MessageForm()
        context = {
            'sujets': sujets,
            'base_template': base_template,
            'Types': nom_session,
            'form': form,
            'mess': mess,
            'sujet': sujet,

        }
    return render(request, 'Forum/detail_sujet.html', context)


def liste_sujets(request):
    sujets = SujetDiscussion.objects.all().order_by('-date_creation')
    nom_session = request.session.get('compte', 'Inconnu')
    # Selection du menu selon le type
    base_template=""
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"

    if nom_session == 'Apprenant':
        base_template = "Menus/MenuEspaceApp.html"
    else:
        base_template = "Menus/Menu.html"

    context={
        'sujets': sujets,
        'base_template': base_template,
        'Types':nom_session
    }
    return render(request, 'Forum/liste_sujets.html', context)


# Gestion Meeting

def generer_lien_meet():
    code = '-'.join(
        [''.join(random.choices(string.ascii_lowercase, k=3)) for _ in range(3)]
    )
    return f'https://meet.google.com/{code}'

# @login_required
# def creer_reunion(request):
#     if request.method == 'POST':
#         form = ReunionForm(request.POST)
#         if form.is_valid():
#             reunion = form.save(commit=False)
#             reunion.formateurs = request.user
#             #reunion.meet_link = generer_lien_meet()
#             reunion.save()
#             form.save_m2m()
#             return redirect('liste_reunions')  # à adapter selon ton URL
#     else:
#         form = ReunionForm()
#     return render(request, 'reunion/creer_reunion.html', {'form': form})

@login_required
def creer_reunions(request):
    nom_session = request.session.get('compte', 'Inconnu')
    mesclasse = MaClasse.objects.filter(username_id=request.user.id)
    #print(mesclasse)
    if request.method == 'POST':
        form = Reunion(
            maclasse_id=request.POST['maclas'],
            titre=request.POST['Titre'],
            description=request.POST['Description'],
            date_debut=request.POST['Datedebut'],
            date_fin=request.POST['Datefin'],
            meet_link=request.POST['lien'],
            formateurs=request.user
        )
        form.save()
        #form.save_m2m()
        return redirect('liste_reunions')  # à adapter selon ton URL
    else:

        form = ReunionForm()
        context = {
            'form': form,
            'mesclasse': mesclasse,
            'nom_session': nom_session,
        }
        return render(request, 'reunion/creer_reunions.html',context)

# ========== Groupe Etude ======================
@login_required
def creer_reunionEtude(request): # modele reunion Groupe Etude
    nom_session = request.session.get('compte', 'Inconnu')
    groups = GroupeEtude.objects.filter(username_id=request.user.id)
    #print(mesclasse)
    if request.method == 'POST':

        forms = ReunionEtude(
            groupeetude_id=request.POST['groupetudeid'],
            titre=request.POST['Titre'],
            description=request.POST['Description'],
            date_debut=request.POST['Datedebut'],
            date_fin=request.POST['Datefin'],
            meet_link=request.POST['lien'],
            apprenants_id=request.user.id
        )
        forms.save()
        #form.save_m2m()
        return redirect('liste_reunionsEtude')  # à adapter selon ton URL
    else:

        form = ReunionEtudeForm()
        context = {
            'form': form,
            'groups': groups,
            'nom_session': nom_session,
        }
        return render(request, 'reunion/creer_reunionsApp.html',context)

@login_required
def liste_reunionsEtude(request): # Liste des reunions du groupe etude

    request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    nom_session = request.session.get('compte', 'Inconnu')
    reunions_list = ReunionEtude.objects.all().order_by("-id")
    paginator = Paginator(reunions_list, 15)  # 15 réunions par page
    page_number = request.GET.get('page')
    page_objList = paginator.get_page(page_number)
    nom_session = request.session.get('compte', 'Inconnu')
    #Selection du menu selon le type
    # if nom_session == 'Formateur':
    #     base_template = "Menus/MenuEspaceForm.html"
    # else:
    #     base_template = "Menus/MenuEspaceApp.html"

    Appren = Apprenants.objects.filter(username_id=request.user.id).first()
    MesGroupe = Appren_GroupeEtude.objects.filter(Matricule=Appren.Matricule)
    mesGroupeEtude = GroupeEtude.objects.filter(
        Q(id__in=MesGroupe.values_list('groupetude_id', flat=True)) | Q(username_id=request.user.id))
    #----------------------
    #mesreunions = ReunionEtude.objects.filter(apprenants_id=request.user.id) # Toutes les reunions de l'utilisateur
    # Les groupes ayant fait objet de reunion
    mesGroupeEtude = ReunionEtude.objects.filter(groupeetude_id__in=mesGroupeEtude.values_list('id', flat=True))

    #========================================Historique==================

    reunions_lists = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion encours
    paginator = Paginator(reunions_lists, 15)  # 15 réunions par page
    page_number = request.GET.get('page')
    page_objLists = paginator.get_page(page_number)
    # Toutes les classes de l'apprenant
    MesCla = apprenant_maclasses.objects.filter(apprenant_id=Appren.Matricule)
    MesClas = MaClasse.objects.filter(id__in=MesCla.values_list('maclasse_id'))
    # les classes objet de reunion                                            )
    mesreunions = Reunion.objects.filter(maclasse_id__in=MesCla.values_list('maclasse_id', flat=True), etat=0)
    # Les classes ayant fait objet de reunion
    mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))

    # ======================Liste des Reunion groupe Etude========================

    #reunions_listEtude = Reunion.objects.filter(etat=0).order_by("-id")  # Toutes les reunion encours
    # Toutes les Groupe etude de l'apprenant
    MesGroupeEtud = Appren_GroupeEtude.objects.filter(Matricule_id=Appren.Matricule)

    MesGroupeEtudes = GroupeEtude.objects.filter(
        Q(id__in=MesGroupeEtud.values_list('groupetude_id', flat=True)) |
        Q(username_id=request.user.id))

    # print(MesGroupeEtude.values())
    # les  reunions                                            )
    mesreunionsEtudes = ReunionEtude.objects.filter(
        groupeetude_id__in=MesGroupeEtudes.values_list('id', flat=True))
    paginator = Paginator(mesreunionsEtudes, 15)  # 15 réunions par page
    page_number = request.GET.get('page')
    page_objReuEtude = paginator.get_page(page_number)
    # print(mesreunionsEtudes.values())
    # Les Groupes ayant fait objet de reunion
    MesGroupes = GroupeEtude.objects.filter(id__in=mesreunionsEtudes.values_list('groupeetude_id', flat=True))

    # # ====================
    # MreunionsEtudes = ReunionEtude.objects.filter(
    #     groupeetude_id__in=MesGroupeEtudes.values_list('id', flat=True), etat=1)
    #
    # # Les Groupes ayant fait objet de reunion
    # MesGroupeEtude = GroupeEtude.objects.filter(id__in=MreunionsEtudes.values_list('groupeetude_id', flat=True))


    #======================================

    context = {
        "Types": nom_session,
        # 'page_obj': page_obj,
        'messages': messages,
        'reunions_list':page_objList,
        'page_number':page_number,
        'mesGroupeEtude':mesGroupeEtude,
        'reunions_lists':page_objLists,
        'MesGroupeEtudes':MesGroupeEtudes,
        'MesClas': MesClas,
        'TotalClasse': MaClasse.objects.filter(username_id=request.user.id).count(),
        'MesGroupes': MesGroupes,
        'mesreunionsEtudes': page_objReuEtude,
        'mesclasse': mesclasse,
        'mesreunions': mesreunions,

        # 'base_template':base_template
    }

    return render(request, 'reunion/liste_reunionsApp.html', context)
# Modifier Reunion

@login_required
def Modifier_reunionEtude(request,pk):
    nom_session = request.session.get('compte', 'Inconnu')
    groups = GroupeEtude.objects.filter(username_id=request.user.id)
    Mareunion = ReunionEtude.objects.get(pk=pk)

    if request.method == 'POST':
        form = ReunionEtudeForm(request.POST or None, instance=Mareunion, user=request.user)
        #form = ReunionEtudeForm(request.POST, instance=Mareunion)

        if form.is_valid():
            form.save()
            return redirect('liste_reunionsEtude')
    else:
        form = ReunionEtudeForm(instance=Mareunion, user=request.user)
        #form = ReunionEtudeForm(instance=Mareunion)

    context = {
        'form': form,
        'groups': groups,
        'nom_session': nom_session,
        'Mareunion': Mareunion,
    }
    return render(request, 'reunion/Modifier_reunionApp.html', context)

def suppreunionEtude(request,pk):
    reunions= ReunionEtude.objects.filter(id=pk)
    reunions.delete()

    #return render(request, 'reunion/liste_reunions.html', context)
    return redirect('liste_reunionsEtude')

# @login_required
# def Modifier_reunion(request,pk):
#     nom_session = request.session.get('compte', 'Inconnu')
#     mesclasse = MaClasse.objects.filter(username_id=request.user.id)
#     Mareunion = Reunion.objects.get(pk=pk)
#
#     if request.method == 'POST':
#         form = ReunionForm(request.POST or None, instance=Mareunion, user=request.user)
#         if form.is_valid():
#             form.save()
#             return redirect('liste_reunions')
#     else:
#         form = ReunionForm(instance=Mareunion, user=request.user)
#
#     context = {
#         'form': form,
#         'mesclasse': mesclasse,
#         'nom_session': nom_session,
#         'Mareunion': Mareunion,
#     }
#     return render(request, 'reunion/Modifier_reunion.html', context)



#===============Reunion groupe de travail=========================

@login_required
def creer_reunionGrpTrav(request): # modele reunion Groupe Travail
    nom_session = request.session.get('compte', 'Inconnu')
    groups = GroupeTravails.objects.filter(username_id=request.user.id)
    #print(mesclasse)
    if request.method == 'POST':

        forms = ReunionGrpTravail(
            groupetravail_id=request.POST['Groupeid'],
            titre=request.POST['Titre'],
            description=request.POST['Description'],
            date_debut=request.POST['Datedebut'],
            date_fin=request.POST['Datefin'],
            meet_link=request.POST['lien'],
            formateurs_id=request.user.id
        )
        forms.save()
        #form.save_m2m()
        return redirect('liste_reunionsGrpTrav')  # à adapter selon ton URL
    else:

        form = ReunionGrpTravailForm()
        context = {
            'form': form,
            'groups': groups,
            'nom_session': nom_session,
        }
        return render(request, 'reunion/creer_reunionsGrpTrav.html',context)

@login_required
def liste_reunionsGrpTrav(request): # Liste des reunions du groupe etude

    reunions_list = ReunionGrpTravail.objects.all().order_by("-id")
    paginator = Paginator(reunions_list, 5)  # 5 réunions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    nom_session = request.session.get('compte', 'Inconnu')
    #Selection du menu selon le type
    # if nom_session == 'Formateur':
    #     base_template = "Menus/MenuEspaceForm.html"
    # else:
    #     base_template = "Menus/MenuEspaceApp.html"
    forma=Formateurs.objects.filter(username_id=request.user.id).first()
    MesGroupe=form_grpe_travails.objects.filter(Matricule=forma.Matricule)
    mesGroupeTrav=GroupeTravails.objects.filter(Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
    #mesreunions = ReunionGrpTravail.objects.filter(formateurs_id=request.user.id) # Toutes les reunions de l'utilisateur
    # Les groupes ayant fait objet de reunion

    reunions_list = ReunionGrpTravail.objects.filter(groupetravail_id__in=mesGroupeTrav.values_list('id', flat=True))

    context = {
        "Types": nom_session,
        'page_obj': page_obj,
        'messages': messages,
        'reunions_list':reunions_list,
        'page_number':page_number,
        'mesGroupeTrav':mesGroupeTrav,
        # 'base_template':base_template
    }

    return render(request, 'reunion/liste_reunionsGrpTrav.html', context)


# Modifier Reunion

@login_required
def Modifier_reunionGrpTrav(request,pk):

    nom_session = request.session.get('compte', 'Inconnu')
    groups = GroupeTravails.objects.filter(username_id=request.user.id)
    Mareunion = ReunionGrpTravail.objects.get(pk=pk)

    if Mareunion.formateurs_id !=request.user.id:
        messages.success(request, "Vous n'avez pas le droit de Modification.")
        return redirect('liste_reunions')

    if request.method == 'POST':
        form = ReunionGrpTravailForm(request.POST or None, instance=Mareunion, user=request.user)
        #form = ReunionEtudeForm(request.POST, instance=Mareunion)

        if form.is_valid():
            form.save()
            return redirect('liste_reunions')
    else:
        form = ReunionGrpTravailForm(instance=Mareunion, user=request.user)
        #form = ReunionEtudeForm(instance=Mareunion)

    context = {
        'form': form,
        'groups': groups,
        'nom_session': nom_session,
        'Mareunion': Mareunion,
    }
    return render(request, 'reunion/Modifier_reunionGrpTrav.html', context)

def suppreunionGrpTrav(request,pk):
    reunions= ReunionGrpTravail.objects.filter(id=pk)
    reunions.delete()
    #return render(request, 'reunion/liste_reunions.html', context)
    return redirect('liste_reunionsGrpTrav')

#=================== Classe ==================================

# @login_required
# def liste_reunions(request):
# 
#     reunions_list = Reunion.objects.all().order_by("-id")
#     paginator = Paginator(reunions_list, 5)  # 5 réunions par page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#     nom_session = request.session.get('compte', 'Inconnu')
#     #Selection du menu selon le type
#     if nom_session == 'Formateur':
#         base_template = "Menus/MenuEspaceForm.html"
#     else:
#         base_template = "Menus/MenuEspaceApp.html"
#
#     mesreunions = Reunion.objects.filter(formateurs_id=request.user.id) # Toutes les reunions de l'utilisateur
#     #mesclasse=MaClasse.objects.filter(id__in=mesreunions)
#     # Les classes ayant fait objet de reunion
#     mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))
#
#     # =============Reunion de Groupe de travail===============
#     forma = Formateurs.objects.filter(username_id=request.user.id).first()
#     MesGroupe = form_grpe_travails.objects.filter(Matricule=forma.Matricule)
#     mesGroupeTrav = GroupeTravails.objects.filter(
#         Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
#     # mesreunions = ReunionGrpTravail.objects.filter(formateurs_id=request.user.id) # Toutes les reunions de l'utilisateur
#     # Les groupes ayant fait objet de reunion
#
#     reunions_listGrpT = ReunionGrpTravail.objects.filter(
#         groupetravail_id__in=mesGroupeTrav.values_list('id', flat=True))
#
#     context = {
#         "Types": nom_session,
#         'page_obj': page_obj,
#         'messages': messages,
#         'reunions_list':reunions_list,
#         'page_number':page_number,
#         'mesclasse':mesclasse,
#         'base_template':base_template,
#         'reunions_listGrpT': reunions_listGrpT,
#         'mesGroupeTrav':mesGroupeTrav,
#
#     }
#
#     return render(request, 'reunion/liste_reunions.html', context)


@login_required
def Modifier_reunion(request,pk):
    nom_session = request.session.get('compte', 'Inconnu')
    mesclasse = MaClasse.objects.filter(username_id=request.user.id)
    Mareunion = Reunion.objects.get(pk=pk)

    if request.method == 'POST':
        form = ReunionForm(request.POST or None, instance=Mareunion, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('liste_reunions')
    else:
        form = ReunionForm(instance=Mareunion, user=request.user)

    context = {
        'form': form,
        'mesclasse': mesclasse,
        'nom_session': nom_session,
        'Mareunion': Mareunion,
    }
    return render(request, 'reunion/Modifier_reunion.html', context)


@login_required
def liste_reunions(request):

    reunions_list = Reunion.objects.all().order_by("-id")
    paginator = Paginator(reunions_list, 5)  # 5 réunions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    nom_session = request.session.get('compte', 'Inconnu')
    #Selection du menu selon le type
    if nom_session == 'Formateur':
        base_template = "Menus/MenuEspaceForm.html"
    else:
        base_template = "Menus/MenuEspaceApp.html"

    mesreunions = Reunion.objects.filter(formateurs_id=request.user.id).order_by('-id') # Toutes les reunions de l'utilisateur
    #mesclasse=MaClasse.objects.filter(id__in=mesreunions)
    # Les classes ayant fait objet de reunion
    mesclasse = MaClasse.objects.filter(id__in=mesreunions.values_list('maclasse_id', flat=True))
    # =============Reunion de Groupe de travail===============
    forma = Formateurs.objects.filter(username_id=request.user.id).first()
    MesGroupe = form_grpe_travails.objects.filter(Matricule=forma.Matricule)
    mesGroupeTrav = GroupeTravails.objects.filter(
        Q(id__in=MesGroupe.values_list('groupetravail_id', flat=True)) | Q(username_id=request.user.id))
    # mesreunions = ReunionGrpTravail.objects.filter(formateurs_id=request.user.id) # Toutes les reunions de l'utilisateur
    # Les groupes ayant fait objet de reunion

    reunions_listGrpT = ReunionGrpTravail.objects.filter(
        groupetravail_id__in=mesGroupeTrav.values_list('id', flat=True)).order_by('-id')

    context = {
        # "Types": nom_session,
        'page_obj': page_obj,
        'messages': messages,
        'reunions_list': reunions_list,
        'page_number': page_number,
        'mesclasse': mesclasse,
        'base_template': base_template,
        'reunions_listGrpT': reunions_listGrpT,
        'mesGroupeTrav': mesGroupeTrav,

    }

    return render(request, 'reunion/liste_reunions.html', context)



def suppreunion(request,pk):
    reunions= Reunion.objects.filter(id=pk)
    reunions.delete()

    #return render(request, 'reunion/liste_reunions.html', context)
    return redirect('liste_reunions')

# Publicité
def page_avec_pub(request):
    pubs = Publicite.objects.filter(actif=True)
    return render(request, 'Publicite.html', {'pubs': pubs})

def CreerPublicite(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    Public = Publicite.objects.filter(actif=True)
    if request.method == 'POST':
        form = PubliciteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Publicité créée avec succès.")
            form = PubliciteForm()  # Réinitialise le formulaire

    else:
        form = PubliciteForm()
    context = {
        'form': form,
        'Public': Public,
        # 'Types': nom_session,
    }
    return render(request, 'CreerPublicite.html', context)

def ModifierPub(request,pk):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    pub = Publicite.objects.get(id=pk)
    Public = Publicite.objects.filter(actif=True)

    if request.method == 'POST':
        form = PubliciteForm(request.POST, request.FILES,instance=pub)
        if form.is_valid():
            form.save()
            messages.success(request, "Publicité Modifié avec succès.")
            return redirect('ModifierPub',pk)  # Remplace par la vue souhaitée
    else:
        form = PubliciteForm(instance=pub)
    context={
        'form': form,
        'Public': Public,
        'pub': pub,
        'pk': pk,
        # 'Types': nom_session,
    }
    return render(request, 'ModifPublicite.html',context)

def SupprimerPub(request,pk):
    pub = Publicite.objects.get(id=pk)
    Public = Publicite.objects.filter(actif=True)
    pub.delete()
    messages.success(request, "Publicité Supprimé avec succès.")
    return redirect('CreerPublicite')

# Cours à domicile
@login_required
def Creercoursdom(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')
    coursDom = CoursAdomicile.objects.filter(actif=True)
    if request.method == 'POST':
        form = CoursAdomForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Cours crée avec succès.")
            form = CoursAdomForm()  # Réinitialise le formulaire

    else:
        form = CoursAdomForm()
    context={
        'form': form,
        'coursDom': coursDom,
        # 'Types': nom_session,
    }
    return render(request, 'CreerCoursAdom.html',context)

def page_coursDom(request):
    cours = CoursAdomicile.objects.filter(actif=True)
    return render(request, 'CoursAdom.html', {'cours': cours})

def ModifierDom(request,pk):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()
    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    cours= CoursAdomicile.objects.get(id=pk)
    coursDom = CoursAdomicile.objects.filter(actif=True)

    if request.method == 'POST':
        form = CoursAdomForm(request.POST, request.FILES,instance=cours)
        if form.is_valid():
            form.save()
            messages.success(request, "Cours à Domicile Modifié avec succès.")
            return redirect('ModifierDom',pk)  # Remplace par la vue souhaitée
    else:
        form = CoursAdomForm(instance=cours)
    context={
            'form':form,
             'coursDom':coursDom,
             'cours':cours,
             'pk':pk,
             # 'Types': nom_session,
             }
    return render(request, 'ModifCoursAdom.html',context)

def SupprimerDom(request,pk):
    cours = CoursAdomicile.objects.get(id=pk)
    coursDom = CoursAdomicile.objects.filter(actif=True)
    cours.delete()
    messages.success(request, "Cours à Domicile Supprimé avec succès.")
    return redirect('Creercoursdom')


# Gestion des etablissements
@login_required
def CreerEtablissement(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    etablis = CentreFormation.objects.filter(actif=True)
    if request.method == 'POST':
        form = CentreFormationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Etablissement crée avec succès.")
            form = CentreFormationForm()  # Réinitialise le formulaire

    else:
        form = CentreFormationForm()
    context = {
        'form': form,
        'etablis': etablis,
        # 'Types': nom_session,
    }
    return render(request, 'CreerEtablissement.html',context)

def page_centreETS(request):
    centres = CentreFormation.objects.filter(actif=True)
    return render(request, 'CoursCentreEts.html', {'centres': centres})


def ModifierEts(request,pk):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    etab = CentreFormation.objects.get(id=pk)
    etablis = CentreFormation.objects.filter(actif=True)

    if request.method == 'POST':
        form = CentreFormationForm(request.POST, request.FILES,instance=etab)
        if form.is_valid():
            form.save()
            messages.success(request, "Etablissement Modifié avec succès.")
            return redirect('ModifierEts',pk)  # Remplace par la vue souhaitée
    else:
     form = CentreFormationForm(instance=etab)
     context={
         'form': form,
         'etablis': etablis,
         'etab': etab,
         'pk': pk,
         # 'Types': nom_session,
     }
    return render(request, 'ModifEtablissement.html',context)



def SupprimerEts(request,pk):
    etablis = CentreFormation.objects.filter(actif=True)
    etab = CentreFormation.objects.get(id=pk)
    etab.delete()
    messages.success(request, "Etablissement Supprimé avec succès.")
    return redirect('CreerEtablissement')

def RechercheCoursDom(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')
    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if request.method == 'POST':
        ListeCoursDom = CoursAdomicile.objects.filter(Discipline=request.POST['Discipline'])

    if ListeCoursDom:

        context = {
            'ListeCoursDom': ListeCoursDom,
            # 'Types': nom_session,
            'Disciple': request.POST['Discipline'],
        }
    else:
        messages.success(request, "Aucun resultat")
    context = {
        'ListeCoursDom': ListeCoursDom,
        # 'Types': nom_session,
        'Disciple':request.POST['Discipline'],
    }
    return render(request, 'ListeCoursAdom.html', context)


def ListeEtablissement(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')
    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    ListeEtable= CentreFormation.objects.all()
    print(ListeEtable.values())


    context = {
        'ListeEtable': ListeEtable,
        # 'Types': nom_session,

    }
    return render(request, 'ListeEtablissement.html', context)
    # else:
    #     messages.success(request, "Aucun resultat")
    # context = {
    #      'ListeEtable': ListeEtable,
    #      'Types': nom_session,
    # }
    # return render(request, 'ListeEtablissement.html', context)


# Gestion des Activation

def generate_secure_code(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

@login_required
def CreerActivation(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    active = Activation.objects.filter()
    if request.method == 'POST':
        # form = ActivationForm(request.POST)
        # if form.is_valid():
        #     form.save()
        code = generate_secure_code()
        VeriMatricule=Apprenants.objects.filter(Matricule=request.POST['Matricule']).first()
        if not VeriMatricule:
            messages.success(request, "Ce matricule n'existe pas.")
            return render(request, 'Activation/CreerActivations.html')

        Activation.objects.create(Matricule_id=request.POST['Matricule'],
                                  CodeActivation=code,
                                  Delais=request.POST['Delais'],
                                  Etat=False
                                  )

        messages.success(request, "Code Activation crée avec succès.")
            # form = ActivationForm()  # Réinitialise le formulaire

    context = {
            # 'form': form,
            'active': active,

    }
    return render(request, 'Activation/CreerActivations.html',context)


def ModifierActivation(request,pk):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    active = Activation.objects.get(id=pk)
    activation = Activation.objects.filter(Etat=False)

    if request.method == 'POST':
        form = ActivationForm(request.POST, request.FILES,instance=active)
        if form.is_valid():
            form.save()
            messages.success(request, "Code d'activation Modifié avec succès.")
            return redirect('CreerActivation')  # Remplace par la vue souhaitée
    else:
     form = ActivationForm(instance=active)
     context={
         'form': form,
         'activation': activation,
         'active': active,
         'pk': pk,

     }
    return render(request, 'Activation/ModifActivation.html',context)


def SupprimerActivation(request,pk):
    active = Activation.objects.get(id=pk)
    activation = Activation.objects.filter()
    active.delete()
    messages.success(request, "Code Activation Supprimé avec succès.")
    return redirect('CreerActivation')  # Remplace par la vue souhaitée


def ListeCodeActivation(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).exists()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    activation = Activation.objects.filter().order_by("Etat")

    context = {
        'activation': activation,

    }
    return render(request, 'Activation/ListeCodeActivation.html',context)

# Activation des comptes Apprenants
def ActivationCompte(request):
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()
    Forma = Formateurs.objects.filter(username_id=request.user.id).exists()

    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        nom_session = request.session.get('compte', 'Inconnu')
        activations = Activation.objects.filter(Q(Matricule_id=Appren.Matricule),Q(Etat=False))
    else :
        # Liste des code d'activation
        activations = Activation.objects.filter(Etat=False)

    context = {
        # 'form': form,
        'activations': activations,

    }
    if request.method == 'POST':
        activa = Activation.objects.filter(CodeActivation=request.POST['CodeActive']).first()

        if not activa:
            messages.success(request, f"Ce Code Activation {request.POST['CodeActive']} n'existe pas.")
            return render(request, 'Activation/PageActivation.html', context)

        #activation = Activation.objects.get(Q(Matricule_id=request.post['CodeActive']),Q(Etat=False))
        Compte=Apprenants.objects.filter(Matricule=activa.Matricule_id).first()

        # Activation du compte Apprenant

        Compte.Delai=activa.Delais
        Compte.actif=True
        Compte.create_at=timezone.now()
        Compte.save()
        # Validation
        activa.Etat=True
        activa.save()
        messages.success(request, f"Code Activation {request.POST['CodeActive']} validé avec succès.")
        return redirect('monespace')
    context={
         # 'form': form,
         'activations': activations,
         # 'Types': nom_session,
     }
    return render(request, 'Activation/PageActivation.html',context)