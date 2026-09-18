from flask import Flask
import json
from sqlalchemy import create_engine
import urllib.parse

path = r"application\config.json"
with open(path,'r') as file:
    MYSQL_CONFIG = json.load(file)

# creation d'une instance d'application
app = Flask(__name__)


# connexion a la base de donnees
user = MYSQL_CONFIG['user']
password = urllib.parse.quote_plus(MYSQL_CONFIG['password'])  # Encodage du mot de passe
host = MYSQL_CONFIG['host']
port = MYSQL_CONFIG['port']
db = MYSQL_CONFIG['database']
connection_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
engine = create_engine(connection_str)




from application import routes