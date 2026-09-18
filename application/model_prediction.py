from application import engine
from application.data_preprocessing import preprocessing_1, preprocessing_2  # type: ignore
import pandas as pd
from sqlalchemy import text
from joblib import load
from xgboost import XGBRegressor




def prediction_jour(date = '2025-04-18'):
    
    
    #Recuperation des champs necessaire pour effectuer la prediction du nombre de connexion
    
    query = text("""
    select   distinct  pcj.day as date, TIME_FORMAT(pcj.heure_from, '%H:%i:%s') as heure_from, TIME_FORMAT(pcj.heure_to, '%H:%i:%s') as heure_to , pcj.id_classe ,ni.titre_fr as niveau,cat.name as category,ty.name as type_cour,ma.titre_fr as matiere, co.nb_heures as nb_heures_cour, co.prix as prix_cour, co.frequence_prix as frequence_prix_cour,pa.prix as prix_parcours, pa.weekly_hours as nb_heures_parcours_par_semaine,pc.type 
			from planning_cours_journaliers as pcj , meetings as me , parcours_classes as pc , cours as co , matieres as ma , classes as ca, parcours as pa ,niveaux as ni , categories as cat , types as ty 
			where pcj.id_classe is not null
			and day = :date_param
			and heure_from is not null
			and heure_to is not null
            and heure_from < heure_to
            and pcj.id_classe = me.id_classe
            and FIND_IN_SET(pcj.id_classe, pc.classes) > 0
            and pcj.id_classe = ca.id
            and ca.id_cours = co.id
            and ni.id = co.id_niveau
            and cat.id  = co.id_category
            and ty.id = co.id_type
            and co.id_matiere = ma.id
            and pc.id_parcours = pa.id
            group by heure_from , heure_to , me.id;        
          
    """)
    with engine.connect() as conn:
        conn.execute(text(
            "SET SESSION sql_mode = "
            "(SELECT REPLACE(@@sql_mode, 'ONLY_FULL_GROUP_BY', ''));"
        ))


    df = pd.read_sql(query, engine, params={"date_param": date})
    if df.empty:
        connexions_day = {}
        for i in range(7,24):
            key = f"{i}"
            connexions_day[key] = 0
        return connexions_day
       
    
    df = preprocessing_1(df)
    df = preprocessing_2(df)
    
    # importation du modele de prediction
    model = load(r"application\xgb_model.joblib")
    
    
    # predictions
    
    features = ['id_classe',
       'nb_heures_cour', 
       'Periode(Vacances)',
       'category_Scolaire_enc', 'type_cour_Soutien Scolaire_enc',
       'matiere_Arabe Classique_enc', 'matiere_Comptabilité_enc',
       'matiere_Economie générale_enc', 'matiere_Francais_enc',
       'matiere_Histoire-géographie_enc', 'matiere_Mathématiques_enc',
       'matiere_Mémorisation de textes\ résolution de problèmes \ connaissance générale\ linguistique sémantique_enc',
       'matiere_Organisation des entreprise_enc', 'matiere_Philosophie_enc',
       'matiere_Physique Chimie_enc', 'matiere_SI_enc', 'matiere_SVT_enc',
       'matiere_éducation islamique_enc', 'frequence_prix_cour_par_mois_enc',
       'type_SEP_enc', 'jour_jeudi_enc', 'jour_lundi_enc', 'jour_mardi_enc',
       'jour_mercredi_enc', 'jour_samedi_enc', 'jour_vendredi_enc',
       'niveau_enc', 'year', 'month', 'dayofweek', 'is_weekend',
       'duree_minutes', 'creneaux', 'nb_heures_courxprix_cour',
       'nb_heures_courxprix_courxprix_parcours', 'prix_cour',
       'prix_parcours','nb_heures_parcours_par_semaine','hour_to', 'minute_to', 'hour_from',
       'minute_from'] 
    
    nb_connexions = model.predict(df[features])

    df['nb_connexions'] = nb_connexions.round().astype(int)

    # Regroupement des connexions en fonctions de l'heure
    
    connexions_day = {}
    for i in range(7,24):
        key = f"{i}"
        connexions_day[key] = 0



    for _, row in df.iterrows():
        for key in connexions_day.keys():
            if row['hour_from'] <= int(key) <= row['hour_to']:
                connexions_day[key] += row['nb_connexions']
    
        
    
    #return df.to_dict(orient="records")  
    return connexions_day

    
    