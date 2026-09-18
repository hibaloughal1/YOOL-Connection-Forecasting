from application import app, engine, model_prediction
from flask import render_template, request, redirect, url_for ,jsonify
from datetime import datetime
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil
from sqlalchemy import text


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/test-db")
def test_db():
    try:
        with engine.connect() as conn:
            # exécution d'une requête simple
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            one = result.scalar()  # devrait valoir 1
        return f"Connexion BD réussie 🎉 (SELECT 1 → {one})"
    except Exception as e:
        # en cas d'erreur, on renvoie le message pour debug
        return f"Échec de la connexion BD : {e}", 500


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
   is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
   if  is_ajax:
       # Requête AJAX : uniquement le graphique horaire
       selected_day = request.args.get('day') or request.form.get('day')
       if not selected_day:
           return jsonify({"error": "No day provided"}), 400

       query_hour_ajax = text("""
                  SELECT DISTINCT
                      pcj.day AS date,
                      pcj.heure_from,
                      pcj.heure_to,
                      COUNT(*) AS nb_connexions
                  FROM planning_cours_journaliers pcj
                  JOIN meetings me ON pcj.id_classe = me.id_classe
                  JOIN participation_meetings pm ON pm.id_meeting = me.id
                    AND pm.planning_cours_journalier_id = pcj.id
                  WHERE pcj.day = :selected_day
                    AND pcj.heure_from IS NOT NULL
                    AND pcj.heure_to IS NOT NULL
                  GROUP BY pcj.day, pcj.heure_from, pcj.heure_to
                  ORDER BY pcj.day;
              """)
       df_hour = pd.read_sql(query_hour_ajax, engine, params={"selected_day": selected_day})

       def extract_hour(t):
           return int(t.total_seconds() // 3600) if pd.notnull(t) else 0

       df_hour['h_start'] = df_hour['heure_from'].apply(extract_hour)
       df_hour['h_end'] = df_hour['heure_to'].apply(extract_hour)

       hour_data = defaultdict(int)
       for _, row in df_hour.iterrows():
           for h in range(row['h_start'], row['h_end'] + 1):
               h_str = str(h).zfill(2)
               hour_data[h_str] += int(row['nb_connexions'])

       full_day = [str(h).zfill(2) for h in range(24)]
       labels = full_day
       values = [hour_data[h] for h in labels]

       return jsonify({
           "labels": labels,
           "values": values
       })
   else:
       # --------- Requête classique (non AJAX) ---------
       start_str = request.args.get("start_date") or request.form.get("start_date", "")
       end_str = request.args.get("end_date") or request.form.get("end_date", "")
       selected_axe = request.args.get('axe', 'niveau').lower()

       # Initialisation des valeurs par défaut
       jours_list = []
       total_connexions = 0
       max_connexions_list = []
       nb_sessions = 0
       total_connexions_journaliers = []
       ratio = 0
       bar_data = {"labels": [], "connexions": []}
       selected_day_hours = []
       selected_day_connexions = []
       available_days = []

       # --- Bloc A : Données dépendantes de start_date et end_date ---
       if start_str and end_str:

           query_connexions = text("""
               SELECT
                   DATE(pm.entree) AS jour,
                   pm.id_meeting,
                   COUNT(DISTINCT pm.id_user) AS connexions
               FROM participation_meetings pm
               JOIN planning_cours_journaliers pcj ON pcj.id = pm.planning_cours_journalier_id
               WHERE pm.entree IS NOT NULL
                 AND pm.entree BETWEEN :start_date AND :end_date
               GROUP BY DATE(pm.entree), pm.id_meeting
               """)

           query_sessions = text("""
               SELECT COUNT(DISTINCT pm.id_meeting) AS nb_sessions
               FROM participation_meetings pm
               WHERE pm.entree IS NOT NULL
                 AND pm.entree BETWEEN :start_date AND :end_date
               """)

           query_total_connexions = text("""
               SELECT COUNT(Distinct pm.id_user) AS total_connexions
               FROM participation_meetings pm
               WHERE pm.entree IS NOT NULL
                 AND pm.entree BETWEEN :start_date AND :end_date
                 """)

           with engine.connect() as conn:
               df_bar = pd.read_sql(query_connexions, conn, params={"start_date": start_str, "end_date": end_str})
               result = conn.execute(query_sessions, {"start_date": start_str, "end_date": end_str})
               nb_sessions = result.scalar()
               result_total = conn.execute(query_total_connexions, {"start_date": start_str, "end_date": end_str})
               total_connexions = result_total.scalar()

           df_bar['jour'] = pd.to_datetime(df_bar['jour'])

           # Agrégation par jour

           all_days = pd.date_range(start=start_str, end=end_str)

           df_journalier = df_bar.groupby('jour').agg(
               total_connexions=('connexions', 'sum'),
               max_connexions=('connexions', 'max')
           )
           df_journalier = df_journalier.reindex(all_days, fill_value=0)  # << clé ici
           df_journalier.index.name = 'jour'
           df_journalier = df_journalier.reset_index()

           jours_list = df_journalier['jour'].dt.strftime('%Y-%m-%d').tolist()
           total_connexions_journaliers = df_journalier['total_connexions'].tolist()
           max_connexions_list = df_journalier['max_connexions'].tolist()
           total_connexions_journaliers = df_journalier['total_connexions'].tolist()
           ratio = round(total_connexions / nb_sessions, 2) if nb_sessions != 0 else 0

           query = """
                   SELECT
                     DATE(pcj.day) AS jour,
                     ni.titre_fr AS niveau,
                     ma.titre_fr AS matiere,
                     cat.name AS categorie,
                     COUNT(*) AS nb_connexions
                   FROM planning_cours_journaliers AS pcj
                   JOIN meetings AS me ON pcj.id_classe = me.id_classe
                   JOIN participation_meetings AS pm ON pm.id_meeting = me.id AND pm.planning_cours_journalier_id = pcj.id
                   JOIN classes AS ca ON pcj.id_classe = ca.id
                   JOIN cours AS co ON ca.id_cours = co.id
                   JOIN matieres AS ma ON co.id_matiere = ma.id
                   JOIN niveaux AS ni ON ni.id = co.id_niveau
                   JOIN categories AS cat ON cat.id = co.id_category
                   WHERE pcj.day BETWEEN %(start_date)s AND %(end_date)s
                   GROUP BY DATE(pcj.day), ni.titre_fr, ma.titre_fr, cat.name
                   ORDER BY DATE(pcj.day);
                   """

           df_bar = pd.read_sql(query, engine, params={'start_date': start_str, 'end_date': end_str})

           # Vérification et choix de colonne valide
           allowed_axes = ['niveau', 'matiere', 'categorie']
           if selected_axe not in allowed_axes:
               selected_axe = 'niveau'
           if selected_axe not in df_bar.columns:
               df_bar[selected_axe] = None

           df_bar.dropna(subset=[selected_axe], inplace=True)

           if selected_axe in df_bar.columns:
               grouped = df_bar.groupby(selected_axe)['nb_connexions'].sum().sort_values(ascending=False)
               labels = list(grouped.index.astype(str))
               connexions = list(grouped.values)
           else:
               labels = []
               connexions = []

           bar_data = {
               'labels': labels,
               'connexions': connexions,
               'axe': selected_axe.capitalize()
           }

       # --- Bloc B : Données dépendantes de selected_day ---
       # --- Connexions par heure pour une journée ---
       df_days = pd.read_sql(text("SELECT DISTINCT day FROM planning_cours_journaliers ORDER BY day DESC"), engine)
       df_days['day'] = pd.to_datetime(df_days['day'], errors='coerce')
       df_days = df_days.dropna(subset=['day'])
       available_days = df_days['day'].dt.strftime("%Y-%m-%d").tolist()

       selected_day = available_days[0] if available_days else None

       # Requête pour données horaires (doit être avant extraction)
       query_hour = text("""
               SELECT DISTINCT
                   pcj.day AS date,
                   pcj.heure_from,
                   pcj.heure_to,
                   COUNT(*) AS nb_connexions
               FROM planning_cours_journaliers pcj
               JOIN meetings me ON pcj.id_classe = me.id_classe
               JOIN participation_meetings pm ON pm.id_meeting = me.id
               AND pm.planning_cours_journalier_id = pcj.id
               WHERE pcj.day = :selected_day
                 AND pcj.heure_from IS NOT NULL
                 AND pcj.heure_to IS NOT NULL
               GROUP BY pcj.day, pcj.heure_from, pcj.heure_to
               ORDER BY pcj.day;
           """)

       df_hour = pd.read_sql(query_hour, engine, params={"selected_day": selected_day})

       def extract_hour(t):
           return int(t.total_seconds() // 3600) if pd.notnull(t) else 0

       df_hour['h_start'] = df_hour['heure_from'].apply(extract_hour)
       df_hour['h_end'] = df_hour['heure_to'].apply(extract_hour)
       #df_hour['date'] = df_hour['date'].astype(str)
       #available_days = sorted(df_hour['date'].unique().tolist())
       #hour_labels = df_hour["heure_from"].astype(str).tolist()
       #hour_values = df_hour["nb_connexions"].tolist()
       #  Normaliser le format de selected_day pour matcher avec df_hour['date']



       day_hour_data = defaultdict(int)
       for _, row in df_hour.iterrows():
           for h in range(row['h_start'], row['h_end'] + 1):
               h_str = str(h).zfill(2)
               day_hour_data[h_str] += int(row['nb_connexions'])

       full_day = [str(h).zfill(2) for h in range(24)]
       selected_day_hours = full_day
       selected_day_connexions = [day_hour_data[h] for h in full_day]

       # --- Rendu ---
       return render_template("dashboard.html",
                              jours=jours_list,
                              max_connexions=[int(val) for val in max_connexions_list],
                              nb_sessions=int(nb_sessions),
                              total_connexions=int(total_connexions),  # total global (tous jours confondus)
                              total_connexions_journaliers=total_connexions_journaliers,  # liste des totaux par jour
                              ratio=float(ratio),
                              start_date=start_str,
                              end_date=end_str,
                              selected_axe=selected_axe,
                              bar_data={
                                  "labels": list(bar_data["labels"]),
                                  "connexions": [int(val) for val in bar_data["connexions"]]
                              },
                              hourly_labels=list(selected_day_hours),
                              hourly_values=[int(val) for val in selected_day_connexions],
                              available_days=available_days,
                              selected_day=selected_day,
                              )




@app.route("/prediction", methods=["GET", "POST"])
def prediction():
    start_str = request.form.get("start_date", "")
    if start_str:
        connexions_day = model_prediction.prediction_jour(date=start_str)
        return render_template("prediction.html", connexions_day=connexions_day, start_date=start_str)
    else:
        connexions_day = {}
        for i in range(7, 24):
            key = f"{i}"
            connexions_day[key] = 0
        return render_template("prediction.html", connexions_day=connexions_day)

