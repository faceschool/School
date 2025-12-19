
from .models import *
from django.shortcuts import get_object_or_404, redirect, render


def global_variable(request):
    # Exemple : récupérer une valeur depuis la base
    Photo=""
    Discipline=""
    Niveaux=""
    Appren = Apprenants.objects.filter(username_id=request.user.id).first()
    Forma = Formateurs.objects.filter(username_id=request.user.id).first()

    TotalFormateur = Formateurs.objects.all().count()
    TotalApprenant = Apprenants.objects.all().count()
    total_visiteurs=0
    delaisRestant = 0
    total_visiteurs = Visitor.visiteurs_uniques_expiration(24)  # visiteurs des dernières 24h
    code=""
    if Forma:
        request.session['compte'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
        code=Forma.CodeAutorisation
        Photo = Forma.Photo
        Discipline=Forma.Discipline

    if Appren:
        request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
        code = Appren.CodeAutorisation
        delaisRestant=Appren.Delai
        Photo = Appren.Photo
        Niveaux=Appren.Niveau

    nom_session = request.session.get('compte', 'Inconnu')
    context = {
               'Types': nom_session,
               'TotalFormateur':TotalFormateur,
               'TotalApprenant':TotalApprenant,
               'total_visiteurs':total_visiteurs,
               'code':code,
               'delaisRestant':delaisRestant,
               'Photo':Photo,
               'Discipline':Discipline,
               'Niveaux':Niveaux,
               }
    return context


    # if Forma:
    #     # request.session['TotalFormateurs'] = get_object_or_404(Formateurs, username_id=request.user.id).Type
    #
    #     request.session['TotalForm']  = request.session.get('TotalForm', 0)
    #     request.session['TotalForm'] =TotalFormateur
    # if Appren:
    #     # request.session['compte'] = get_object_or_404(Apprenants, username_id=request.user.id).Type
    #
    #     request.session['TotalAppren'] = request.session.get('TotalAppren', 0)
    #     request.session['TotalAppren']=TotalApprenant