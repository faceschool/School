from django.conf.urls.static import static
from django.urls import path,include
from .views import *
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.contrib.auth.views import *
from . import views
urlpatterns = [

        path('', home, name='home'),
       # path('accounts/', include('django.contrib.auth.urls')),
        #path('accounts/', include('django.contrib.auth.urls')),  # inclut /logout/
       # path('logout/', include('django.contrib.auth.urls')),  # inclut /logout/
        path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
        path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
        #path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
        path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'),
             name='password_reset'),
        path('password_reset/done/',
             auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
             name='password_reset_done'),
        path('reset/<uidb64>/<token>/',
             auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
             name='password_reset_confirm'),
        path('reset/done/',
             auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
             name='password_reset_complete'),

        path('register/', register, name='register'),
        path('confirmation/<str:token>/', views.confirmation_inscription, name='confirmation_inscription'),
        path('autorisation/', autorisation, name='autorisation'),
        #path('registers/',views.registers.as_view(), name='registers'),
        path('Profil/', Profil, name='Profil'),

        path('presentation',presentation,name='presentation'),
        path('services', services, name='services'),
        path('contacts', contacts, name='contacts'),
        path('formateurs',formateurs,name='formateurs'),
        path('apprenant', apprenant, name='apprenant'),
        path('Profilformateurs',Profilformateurs,name='Profilformateurs'),

        path('Profilapprenant', Profilapprenant, name='Profilapprenant'),
        path('AffProfil/<int:pk>', AffProfil, name='AffProfil'),
        path('ProfilModifier/<int:pk>', ProfilModifier, name='ProfilModifier'),
        path('update_ProfilApprenant/<int:pk>', update_ProfilApprenant, name='update_ProfilApprenant'),
        path('update_ProfilFormateur/<int:pk>', update_ProfilFormateur, name='update_ProfilFormateur'),
#Info
        path('infoApprenant', infoApprenant, name='infoApprenant'),
        path('infoFormateur', infoFormateur, name='infoFormateur'),
        path('infogroupetude', infogroupetude, name='infogroupetude'),
        path('infogroupeTravail',infogroupeTravail, name='infogroupeTravail'),
# Classe
        path('MesClasses', MesClasses, name='MesClasses'),
        path('LesClasses', LesClasses, name='LesClasses'),
        path('AjouterClasses', AjouterClasses, name='AjouterClasses'),
        path('CreerClasses', CreerClasses, name='CreerClasses'),
        path('ModifClasses/<int:pk>',  ModifClasses, name='ModifClasses'),
        path('UpdateClasses/<int:pk>', UpdateClasses, name='UpdateClasses'),
        path('SuppClasses/<int:pk>', SuppClasses, name='SuppClasses'),
        path('AjouterApprClasses/<int:pk>', AjouterApprClasses, name='AjouterApprClasses'),
        path('InscrireApprClasses/<int:pk>', InscrireApprClasses, name='InscrireApprClasses'),
        path('CodeInscrireApprClasses', CodeInscrireApprClasses, name='CodeInscrireApprClasses'),
        path('AjouterParCode', AjouterParCode, name='AjouterParCode'),
        path('infoClasses', infoClasses, name='infoClasses'),

        path('SupAppClasses/<int:pk>', SupAppClasses, name='SupAppClasses'),
        path('TransferpartClasses', TransferpartClasses, name='TransferpartClasses'),
        path('ListeApprClasses/<int:pk>', ListeApprClasses, name='ListeApprClasses'),

# Gestion des docClasse
        path('Ajouter_document/<int:classe_id>', Ajouter_document, name='Ajouter_document'),
        path('SupDocuments/<int:pk>', SupDocuments, name='SupDocuments'),
        path('Modifier_document/<int:pk>', Modifier_document, name='Modifier_document'),
        path('Transfert_document/<int:pk>', Transfert_document, name='Transfert_document'),
        path('Ajouter_dossiers/<int:pk>', views.Ajouter_dossiers, name='Ajouter_dossiers'),
        path('Modifier_Dossiers/<int:pk>', Modifier_Dossiers, name='Modifier_Dossiers'),
        path('SupDossiers/<int:pk>', SupDossiers, name='SupDossiers'),
        path('ListeDocumentPartFil/<int:pk>', ListeDocumentPartFil,name='ListeDocumentPartFil'),
        path('ListeDossiersPartType/<int:pk>/<str:type_doc>/', ListeDossiersPartType,name='ListeDossiersPartType'),
        path('ListeDocClasses/<int:pk>', ListeDocClasses, name='ListeDocClasses'),
        path('ListeDocumentPartPublic/<str:type_doc>', ListeDocumentPartPublic, name='ListeDocumentPartPublic'),
        path('ListeDocumentPartPublicDisc/<str:type_doc>/<str:Disc>', ListeDocumentPartPublicDisc, name='ListeDocumentPartPublicDisc'),
        path('ListeDocParMatierePublic/<str:Matiere>', ListeDocParMatierePublic,name='ListeDocParMatierePublic'),
        path('ListeDocMatierePartPublicDisc/<str:Matiere>/<str:type_doc>', ListeDocMatierePartPublicDisc, name='ListeDocMatierePartPublicDisc'),
        path('classe/<int:classe_id>/', views.classe_documents, name='classe_documents'),#classe_documents
        path('classe/<int:classe_id>/data/', views.doc_list_data, name='doc_list_data'),  # DataTables server-side

# Mes messages Classes :Ajouter_MessagesClasse
        path('Ajouter_MessagesClasse/<int:pk>', Ajouter_MessagesClasse,name='Ajouter_MessagesClasse'),
        path('Supp_MessagesClasse/<int:pk>', Supp_MessagesClasse,name='Supp_MessagesClasse'),
        path('Liste_MessagesClasse/<int:pk>', Liste_MessagesClasse,name='Liste_MessagesClasse'),
        path('MesMessages', MesMessages,name='MesMessages'),

# Mes messages Groupes Travail : Ajouter Messages Groupes
        path('Ajouter_MessagesGroupeTrav/<int:pk>', Ajouter_MessagesGroupeTrav,name='Ajouter_MessagesGroupeTrav'),
        path('Liste_MessagesGrpTrav/<int:pk>', Liste_MessagesGrpTrav,name='Liste_MessagesGrpTrav'),
        path('Supp_MessagesGrpTrav/<int:pk>', Supp_MessagesGrpTrav, name='Supp_MessagesGrpTrav'),
        path('MesMessages', MesMessages,name='MesMessages'),
        path('Liste_MessagesParGrpTrav/<int:pk>', Liste_MessagesParGrpTrav,name='Liste_MessagesParGrpTrav'),

# Mes messages Groupes Etude : Ajouter Messages Groupes
        path('Ajouter_MessagesGroupeEtude/<int:pk>', Ajouter_MessagesGroupeEtude,name='Ajouter_MessagesGroupeEtude'),
        path('Liste_MessagesGrpEtude/<int:pk>', Liste_MessagesGrpEtude,name='Liste_MessagesGrpEtude'),
        path('Supp_MessagesGrpEtude/<int:pk>', Supp_MessagesGrpEtude, name='Supp_MessagesGrpEtude'),
        path('MesMessages', MesMessages,name='MesMessages'),
        path('Liste_MessagesParGrpEtude/<int:pk>', Liste_MessagesParGrpEtude, name='Liste_MessagesParGrpEtude'),

# Solution
        path('Ajouter_Solution/<int:pk>', Ajouter_Solution, name='Ajouter_Solution'),
        path('SupSolution/<int:pk>', SupSolution, name='SupSolution'),
        path('Ajouter_Note/<int:pk>', Ajouter_Note, name='Ajouter_Note'),
        path('notation/<int:pk>', notation, name='notation'),

#Gestion des Partenariats
        path('CreerPartenariatClasses/<int:pk>', CreerPartenariatClasses, name='CreerPartenariatClasses'),
        path('ListepartClassesApp', ListepartClassesApp, name='ListepartClassesApp'),
        path('ListepartClasses', ListepartClasses, name='ListepartClasses'),
        path('SuppPartenariat/<int:pk>', SuppPartenariat, name='SuppPartenariat'),
        path('ListeDocumentPart/<int:pk>', ListeDocumentPart, name='ListeDocumentPart'),
        path('ListepartMaClasse/<int:pk>', ListepartMaClasse, name='ListepartMaClasse'),
        path('ListeDocumentPartMaClasse/<int:pk>', ListeDocumentPartMaClasse, name='ListeDocumentPartMaClasse'),
        path('ListeDocumentPartClasseFil/<int:pk>', ListeDocumentPartClasseFil, name='ListeDocumentPartClasseFil'),


#GROUPE DE ETUDE
        path('groupetude',groupetude,name='groupetude'),
        path('ModifGroupeEtude/<int:pk>', ModifGroupeEtude, name='ModifGroupeEtude'),
        path('Ajouter_dossiersGrpEtude/<int:pk>', Ajouter_dossiersGrpEtude, name='Ajouter_dossiersGrpEtude'),
        path('Modifier_DossiersGrpEtude/<int:pk>', Modifier_DossiersGrpEtude,name='Modifier_DossiersGrpEtude'),
        path('Supp_DossiersGrpEtude/<int:pk>', Supp_DossiersGrpEtude,name='Supp_DossiersGrpEtude'),
        path('SupGroupeEtude/<int:pk>', SupGroupeEtude,name='SupGroupeEtude'),
        path('AjouterApprenGrpEtude/<int:pk>', AjouterApprenGrpEtude, name='AjouterApprenGrpEtude'),
        path('SupMembreGroupeEtude/<int:pk>', SupMembreGroupeEtude, name='SupMembreGroupeEtude'),
        path('CreerPartenariatGrpEtude/<int:pk>', CreerPartenariatGrpEtude, name='CreerPartenariatGrpEtude'),
        path('ListeDocumentPartGrpEtude/<int:pk>', ListeDocumentPartGrpEtude,name='ListeDocumentPartGrpEtude'),
        path('SuppPartenariatGrpEtude/<int:pk>', SuppPartenariatGrpEtude, name='SuppPartenariatGrpEtude'),
        path('ListeDocGRPEtudePartenTypeDoc/<int:pk>/<str:type_doc>/', ListeDocGRPEtudePartenTypeDoc,
                           name='ListeDocGRPEtudePartenTypeDoc'),
        path('ListepartGrpEtude', ListepartGrpEtude, name='ListepartGrpEtude'),
        path('Transfert_documentGrpEtude/<int:pk>', Transfert_documentGrpEtude, name='Transfert_documentGrpEtude'),

#GROUPE DE TRAVAIL
        path('GroupeTrav',GroupeTrav, name='GroupeTrav'),
        path('ModifGroupeTrav/<int:pk>',ModifGroupeTrav, name='ModifGroupeTrav'),
        path('SupGroupeTrav/<int:pk>', SupGroupeTrav, name='SupGroupeTrav'),
        path('AjouterFormGrpTrav/<int:pk>', AjouterFormGrpTrav, name='AjouterFormGrpTrav'),
        path('SupMembreGroupeTrav/<int:pk>', SupMembreGroupeTrav, name='SupMembreGroupeTrav'),
        path('Ajouter_dossiersGrpTrav/<int:pk>', Ajouter_dossiersGrpTrav, name='Ajouter_dossiersGrpTrav'),
        path('ListeDocGRPTravPartType/<int:pk>/<str:type_doc>/', ListeDocGRPTravPartType,
                           name='ListeDocGRPTravPartType'),
        path('Modifier_DossiersGrpTrav/<int:pk>', Modifier_DossiersGrpTrav, name='Modifier_DossiersGrpTrav'),
        path('Supp_DossiersGrpTrav/<int:pk>', Supp_DossiersGrpTrav, name='Supp_DossiersGrpTrav'),
        path('Transfert_documentGrpTrav/<int:pk>', Transfert_documentGrpTrav, name='Transfert_documentGrpTrav'),
        path('CreerPartenariatGrpTrav/<int:pk>', CreerPartenariatGrpTrav, name='CreerPartenariatGrpTrav'),
        path('ListeDocumentPartGrpTrav/<int:pk>', ListeDocumentPartGrpTrav, name='ListeDocumentPartGrpTrav'),
        path('ListeDocGRPTravPartenTypeDoc/<int:pk>/<str:type_doc>/', ListeDocGRPTravPartenTypeDoc,
                           name='ListeDocGRPTravPartenTypeDoc'),
        path('SuppPartenariatGrpTrav/<int:pk>', SuppPartenariatGrpTrav,name='SuppPartenariatGrpTrav'),#Suppression partenariat
        path('ListepartGrpTrav', ListepartGrpTrav, name='ListepartGrpTrav'),


        path('monespace', monespace, name='monespace'),
        path('monespaceVideo', monespaceVideo, name='monespaceVideo'),

#path('forum', forum, name='forum'),
        path('forum/', views.liste_sujets, name='forum'),
        path('forum/nouveau/', views.nouveau_sujet, name='nouveau_sujet'),
        path('forum/<int:pk>/', views.detail_sujet, name='detail_sujet'),

#Meeting Formateur
        path('reunion/creer/', views.creer_reunions, name='creer_reunions'),
        path('reunion/liste/', views.liste_reunions, name='liste_reunions'),
        path('reunion/supprimer/<int:pk>/', views.suppreunion, name='suppreunion'),
        path('reunion/modifier/<int:pk>/', views.Modifier_reunion, name='modifier'),

#Meeting Groupe Travaux
        path('reunion/creerGrpTrav/', views.creer_reunionGrpTrav, name='creer_reunionGrpTrav'),
        path('reunion/listeGrpTrav/', views.liste_reunionsGrpTrav, name='liste_reunionsGrpTrav'),
        path('reunion/supprimerGrpTrav/<int:pk>/', views.suppreunionGrpTrav, name='suppreunionGrpTrav'),
        path('reunion/modifierGrpTrav/<int:pk>/', views.Modifier_reunionGrpTrav, name='Modifier_reunionGrpTrav'),

#Meeting Apprenant
        path('reunion/creerEtude/', views.creer_reunionEtude, name='creer_reunionEtude'),
        path('reunion/listeEtude/', views.liste_reunionsEtude, name='liste_reunionsEtude'),
        path('reunion/supprimerEtude/<int:pk>/', views.suppreunionEtude, name='suppreunionEtude'),
        path('reunion/modifierEtude/<int:pk>/', views.Modifier_reunionEtude, name='Modifier_reunionEtude'),

        path('ajouter_ProfilFormateur', ajouter_ProfilFormateur, name='ajouter_ProfilFormateur'),
        path('ajouter_ProfilApprenant', ajouter_ProfilApprenant, name='ajouter_ProfilApprenant'),

#Meeting Publicité
        path('page_avec_pub', page_avec_pub, name='page_avec_pub'),
        path('CreerPublicite', CreerPublicite, name='CreerPublicite'),
        path('ModifierPub/<int:pk>/', ModifierPub, name='ModifierPub'),
        path('SupprimerPub/<int:pk>/', SupprimerPub, name='SupprimerPub'),

#Cours à Domicile
        path('page_coursDom', page_coursDom, name='page_coursDom'),
        path('Creercoursdom', Creercoursdom, name='Creercoursdom'),
        path('ModifierDom/<int:pk>/', ModifierDom, name='ModifierDom'),
        path('SupprimerDom/<int:pk>/', SupprimerDom, name='SupprimerDom'),
        path('RechercheCoursDom', RechercheCoursDom, name='RechercheCoursDom'),

#Centre Etablissement
        path('page_centreETS', page_centreETS, name='page_centreETS'),
        path('CreerEtablissement', CreerEtablissement, name='CreerEtablissement'),
        path('ModifierEts/<int:pk>/', ModifierEts, name='ModifierEts'),
        path('SupprimerEts/<int:pk>/', SupprimerEts, name='SupprimerEts'),
        path('ListeEtablissement', ListeEtablissement, name='ListeEtablissement'),

#Code Activation
        path('CreerActivation', CreerActivation, name='CreerActivation'),
        path('ModifierActivation/<int:pk>/', ModifierActivation, name='ModifierActivation'),
        path('SupprimerActivation/<int:pk>/', SupprimerActivation, name='SupprimerActivation'),
        path('ListeCodeActivation', ListeCodeActivation, name='ListeCodeActivation'),
        path('ActivationCompte', ActivationCompte, name='ActivationCompte'),

# Gestion des Stockage et paiement
        path("stockage_page/", views.stokage_page, name="stockage_page"),
        path("demande_quota/", views.demande_quota, name="demande_quota"),
        path("payment/start/<int:request_id>/", views.payment_start, name="payment_start"),
        path("payment/webhook/", views.payment_webhook, name="payment_webhook"),
        path("fake_payment_simulator/<int:request_id>/", fake_payment_simulator, name="fake_payment_simulator"),
        path("fake_payment/<int:request_id>/", fake_payment, name="fake_payment"),
# admin
        path("Admin/quota-requests/", views.admin_list_requests, name="admin_list_requests"),
        path("Admin/quota-requests/<int:pk>/process/", views.admin_process_request,
                           name="admin_process_request"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
