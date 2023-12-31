from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy

projet = Flask(__name__)
projet.secret_key = "hello"
projet.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cuisine.sqlite3'
projet.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
projet.permanent_session_lifetime = timedelta(minutes=5)

db = SQLAlchemy(projet)

class login(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True)
    mdp = db.Column(db.String(50))

    def __init__(self, nom, mdp):
        self.nom = nom
        self.mdp = mdp

class ingredients(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    ingredient = db.Column(db.String(50, collation='NOCASE'), unique=True)

    def __init__(self, ingredient):
        self.ingredient = ingredient

class recettes(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    recettes = db.Column(db.String(50))
    ingredient = db.Column(db.String(50, collation='NOCASE'), unique=True)
    etapes = db.Column(db.String(100))
    quantité = db.Column(db.Integer)
    
    def __init__(self, ingredient, etapes):
        self.ingredient = ingredient
        self.etapes = etapes

@projet.route("/", methods=["POST", "GET"])
def id():
    if request.method == "POST":
        session.permanent = True
        utilisateur = request.form.get("nom")
        mot_de_passe = request.form.get("mdp")

        utilisateur_trv = login.query.filter_by(nom=utilisateur).first()

        if utilisateur_trv:
            # Username exists, check the password
            if utilisateur_trv.mdp == mot_de_passe:
                return redirect(url_for("base"))
            else:
                flash("Mot de passe incorrect. Veuillez réessayer.", "error")
                return redirect(url_for("id"))
        else:
            # Username doesn't exist, create a new entry
            if not utilisateur or not mot_de_passe:
                flash("Veuillez saisir à la fois le nom d'utilisateur et le mot de passe.")
                return redirect(url_for("id"))
            else:
                nv_utilisateur = login(nom=utilisateur, mdp=mot_de_passe)
                db.session.add(nv_utilisateur)
                db.session.commit()
                return redirect(url_for("base"))
    else:
        return render_template("id.html")

@projet.route("/ingredients")
def initdb_and_ingredients():
    with projet.app_context():
        db.create_all()

        # Liste des ingrédients à vérifier et à ajouter
        ingredients_list = [
            "Sel", "Poivre", "Huile d'olive", "Ail", "Oignon", "Basilic",
            "Thym", "Romarin", "Persil", "Ciboulette", "Coriandre", "Menthe",
            "Paprika", "Cumin", "Curcuma", "Moutarde", "Vinaigre balsamique",
            "Vinaigre de vin rouge", "Sauce soja", "Miel", "Sirop d'érable",
            "Citron", "Jus d'orange", "Tomate", "Concentré de tomate",
            "Pomme de terre", "Carotte", "Poivron", "Courgette", "Brocoli",
            "Champignon", "Épinards", "Laitue", "Poisson", "Poulet", "Bœuf",
            "Pâtes", "Riz", "Quinoa", "Farine", "Sucre", "Œuf", "Fromage",
            "Crème fraîche", "Yaourt", "Noix", "Amandes", "Pignons de pin", "Cacahuette", "Salade"
        ]

        try:
            # Vérifiez si les ingrédients existent dans la base de données
            ingr_exist = ingredients.query.filter(ingredients.ingredient.in_(ingredients_list)).all()

            if not ingr_exist:
                # Ajoutez les ingrédients s'ils n'existent pas
                ingredients_to_add = [ingredients(ingredient=ingr) for ingr in ingredients_list]
                db.session.add_all(ingredients_to_add)
                db.session.commit()

        except Exception as e:
            flash(f"Une erreur est survenue lors de l'ajout des ingrédients : {e}", "error")

    ingr_list = ingredients.query.all()
    return render_template("ingr.html", ingr_list=ingr_list)

@projet.route("/search_ingredient", methods=["POST"])
def search_ingredient():
    search_query = request.form.get("search_query")

    if search_query:
        # Effectuez la recherche dans la base de données en ignorant la casse
        search_results = ingredients.query.filter(ingredients.ingredient.ilike(f"%{search_query}%")).all()
    else:
        # Si la requête de recherche est vide, affichez tous les ingrédients
        search_results = None

    ingr_list = ingredients.query.all()
    return render_template("ingr.html", ingr_list=ingr_list, search_results=search_results)

@projet.route("/base")
def base():
    return render_template("base.html")

@projet.route("/recettes")
def rect():
    return render_template("rect.html")

if __name__ == "__main__":
    with projet.app_context():
        db.create_all()

    projet.run(debug=True)
