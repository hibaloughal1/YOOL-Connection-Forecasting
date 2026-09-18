import pandas as pd
import numpy as np
import locale
from sklearn.preprocessing import OneHotEncoder
from datetime import datetime, time, date


df_train = pd.read_csv("application/yool-v2_train_2.csv")

def preprocessing_1(df):
    # Remplir les NaN
    numeriques = df.select_dtypes(include=[np.number]).columns
    catégorielles = df.select_dtypes(exclude=[np.number]).columns

    
    df[numeriques] = df[numeriques].fillna(df[numeriques].mean())
    df[catégorielles] = df[catégorielles].fillna("unknown")


    # ajout de la colonne Periode(Vacances)
    
    holidays = [
    (pd.Timestamp('2023-10-15'), pd.Timestamp('2023-10-22')),
    (pd.Timestamp('2023-12-03'), pd.Timestamp('2023-12-10')),
    (pd.Timestamp('2024-01-22'), pd.Timestamp('2024-01-28')),
    (pd.Timestamp('2024-03-10'), pd.Timestamp('2024-03-17')),
    (pd.Timestamp('2024-04-28'), pd.Timestamp('2024-05-05')),
    (pd.Timestamp('2025-12-21'), pd.Timestamp('2025-01-06')),
    (pd.Timestamp('2025-02-22'), pd.Timestamp('2025-03-10')),
    (pd.Timestamp('2025-04-26'), pd.Timestamp('2025-05-12')),]

    df['date'] = pd.to_datetime(df['date'],format='mixed')
    def IsHolidays(date):
        
        for debut,fin in holidays:
            if date >= debut and date <= fin:
                return 0 ## YES
        return 1 ## NO

    df['Periode(Vacances)'] = df.apply(lambda x: IsHolidays(x['date']),axis=1) 
    
    
    
    
    # ajout de la colonne jour
    
    locale.setlocale(locale.LC_TIME, 'French_France.1252')
    date_obj = df.apply(lambda x: date(x['date'].year, x['date'].month, x['date'].day), axis=1)
    noms_jour = date_obj.map(lambda x: x.strftime('%A'))
    df['jour'] = noms_jour   
    
    # mise a jour de la colonne niveau
    df.loc[
    (df['niveau'] == 'Non définie') &
    (df['category'] == 'Concours & examens') &
    (df['type_cour'] == 'Cours'),
    'niveau'] = 'Post Bac'    
    
    df['niveau'] = df['niveau'].replace({'2ème année Baccalauréat':'2ème année Bac','1ère année Baccalauréat ':'1ère année Bac'})
    
    return df



def date_preprocessing(df):
    """_summary_
        Le but de cette fonction est de decomposer une date sous la forme : Year - Month - DayofWeek - is_Weekend
    Args:
        df (data_frame): un jeu de donne qui contient une colone de type datetime 
    """
    
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day
    df['dayofweek'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['dayofweek'].isin([5,6]).astype(int)
    
    df = df.drop(['date'],axis=1)
    return df   




def time_preprocessing(df):
    """_summary_
        Cette fonction change le format des features heure_from et heure_to et ajoute une nouvelle colonne duree ainsi que celle du creneaux
    Args:
        df (dataframe): 
    """    
   
    df['heure_from_dt'] = pd.to_datetime(df['heure_from'], format='%H:%M:%S', errors='coerce')
    df['heure_to_dt'] = pd.to_datetime(df['heure_to'], format='%H:%M:%S', errors='coerce')
    df['duree_minutes'] = (df['heure_to_dt'] - df['heure_from_dt']).dt.total_seconds() / 60
    
    def creneaux_creation(heure):
        
        # Extraire seulement l'heure sous forme de string HH:MM:SS si nécessaire
        heure = pd.to_datetime(heure, format='%H:%M:%S', errors='coerce')
        heure_only = heure.time()

        
        if time(0, 0) <= heure_only < time(12, 0):
            return 'matin'
        elif time(12, 0) <= heure_only < time(19, 0):
            return 'après-midi'
        elif time(19, 0) <= heure_only <= time(23, 59):
            return 'soir'
        else:
            return 'invalide'

    
    df['creneaux'] = df.apply(lambda x: creneaux_creation(x['heure_from_dt']),axis=1)
    df = df.drop(['heure_from_dt','heure_to_dt'],axis=1)
    
    return df

def features_merging(df,feature_1,feature_2): #nb_heure_cour #prix_cour #prix_parcours
    
    new_feature = feature_1 + "x" + feature_2
    df[new_feature] = df[feature_1] * df[feature_2]
    return df
    
    


def encoding(df):
    cat_features = ['category','type_cour','matiere','frequence_prix_cour','type','jour']

    #1-Fit the encoder only on training data
    encoder = OneHotEncoder(drop='first', handle_unknown='ignore', sparse_output=False)
    encoder.fit(df_train[cat_features])  # only use df_train here

    #2- Transform your DataFrame

    encoded_array = encoder.transform(df[cat_features])

    #3-Get the encoded column names

    encoded_col_names = encoder.get_feature_names_out(cat_features)

    #4-Convert to DataFrame

    df_encoded = pd.DataFrame(encoded_array, columns=encoded_col_names, index=df.index)
    df_encoded = df_encoded.add_suffix('_enc')


    #5- Merge encoded columns into original DataFrame

    df = pd.concat([df, df_encoded], axis=1)    
    
    
    order_map= {'1ère année Collège': 1 ,
                            '2ème année Collège': 2 ,
                            '3ème année Collège': 3 ,
                            '1ère année Bac': 4 ,
                            '2ème année Bac': 5 ,
                            'Post Bac' : 6
                            }
    
    df['niveau_enc'] = df['niveau'].map(order_map).fillna(0).astype(int)
    
    return df
    
  
  
def preprocessing_2(df):
    
    df = encoding(df)  
    
    df = date_preprocessing(df)
    df = time_preprocessing(df)
    df = features_merging(df,'nb_heures_cour','prix_cour')
    df = features_merging(df,'nb_heures_courxprix_cour','prix_parcours')

    creneaux_map = { 'matin' : 0,
                                    'après-midi' : 1,
                                    'soir' : 2}
    df['creneaux'] = df['creneaux'].map(creneaux_map)
    df['creneaux'] =df['creneaux'].astype('int')
    
    
    df['heure_to'] = pd.to_datetime(df['heure_to'], format='%H:%M:%S')

    # Extraction des composantes
    df['hour_to']   = df['heure_to'].dt.hour      # 0–23
    df['minute_to'] = df['heure_to'].dt.minute    # 0–59
    df['second_to'] = df['heure_to'].dt.second    # 0–59

    df['heure_from'] = pd.to_datetime(df['heure_from'], format='%H:%M:%S')

    df['hour_from']   = df['heure_from'].dt.hour      # 0–23
    df['minute_from'] = df['heure_from'].dt.minute    # 0–59
    df['second_from'] = df['heure_from'].dt.second    # 0–59


    df = df.drop(['heure_to','heure_from'],axis = 1)

    
    obj_cols = df.select_dtypes(include='int32').columns
    df[obj_cols] = df[obj_cols].apply(lambda col: col.astype('int64'))
    
    obj_cols = df.select_dtypes(include='float32').columns
    df[obj_cols] = df[obj_cols].apply(lambda col: col.astype('float64'))
    
    return df