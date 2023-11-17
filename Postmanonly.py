from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from enum import Enum
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class MealType(Enum):
    ENTREE = "Entrée"
    PLAT = "Plat"
    DESSERT = "Dessert"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    ingredient_quantities = db.relationship('IngredientQuantity', lazy=True)
    meal_type = db.Column(db.Enum(MealType), nullable=True)
    steps = db.Column(db.Text, nullable=True)
    servings = db.Column(db.Integer, nullable=True)
    ingredient_quantities = db.relationship('IngredientQuantity', back_populates='recipe', lazy=True)




recipe_ingredient = db.Table('recipe_ingredient',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
    db.Column('ingredient_id', db.Integer, db.ForeignKey('ingredient.id'), primary_key=True)
)

class IngredientQuantity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=True)
    ingredient = db.relationship('Ingredient', backref=db.backref('ingredient_quantities'), lazy=True)
    recipe = db.relationship('Recipe', lazy=True)
    ingredient = db.relationship('Ingredient', lazy=True)
    unit = db.Column(db.String(20), nullable=True)

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(MealType), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    entree_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=True)
    plat_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=True)
    dessert_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=True)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    recipe = db.relationship('Recipe', backref=db.backref('favorites'), lazy=True)



# ...

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()

    # Normaliser la casse du nom d'utilisateur
    username = data['username'].lower()

    # Rechercher l'utilisateur dans la base de données par nom d'utilisateur
    existing_user = User.query.filter(func.lower(User.username) == username).first()

    if existing_user:
        # Vérifier le mot de passe
        if check_password_hash(existing_user.password, data['password']):
            return jsonify({"message": "Connecté"}), 200
        else:
            return jsonify({"error": "Mot de passe incorrect"}), 401
    else:
        # Créer un nouvel utilisateur
        new_user = User(username=username, password=generate_password_hash(data['password']))
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User créé avec succès"}), 201




@app.route('/ingredients', methods=['POST', 'GET'])
def manage_ingredients():
    if request.method == 'POST':
        data = request.get_json()
        return create_ingredient(data)
    elif request.method == 'GET':
        return get_all_ingredients()

def create_ingredient(data):
    # Normaliser la casse du nom d'ingrédient
    ingredient_name = data.get('name', '').lower()

    # Vérifier si le nom d'ingrédient existe déjà (en ignorant la casse)
    existing_ingredient = Ingredient.query.filter(func.lower(Ingredient.name) == ingredient_name).first()
    if existing_ingredient:
        return jsonify({"error": "Nom d'ingrédient déjà existant. Veuillez réessayer."}), 400

    # Créer un nouvel ingrédient
    new_ingredient = Ingredient(name=ingredient_name)
    
    try:
        db.session.add(new_ingredient)
        db.session.commit()
    except Exception as e:
        # En cas d'erreur, annuler la transaction
        db.session.rollback()
        return jsonify({"error": f"Erreur lors de la création de l'ingrédient : {str(e)}"}), 500

    return jsonify({"message": "Ingrédient créé avec succès"}), 201

def get_all_ingredients():
    ingredients = Ingredient.query.all()
    ingredient_list = [ingredient.name for ingredient in ingredients]
    return jsonify({"ingredients": ingredient_list})


@app.route('/recipes', methods=['POST', 'GET'])
def manage_recipes():
    if request.method == 'POST':
        return create_recipe()
    elif request.method == 'GET':
        return get_all_recipes()

def get_all_recipes():
    recipes = Recipe.query.all()
    recipe_list = [{"name": recipe.name, "meal_type": recipe.meal_type.value} for recipe in recipes]
    return jsonify({"recipes": recipe_list})

def get_recipes():
    ingredient_name = request.args.get('ingredient_name')

    if ingredient_name:
        # Appeler la fonction de recherche filtrée
        return get_filtered_recipes(ingredient_name)
    else:
        # Sinon, obtenir toutes les recettes
        return get_all_recipes()

def get_filtered_recipes(ingredient_name):
    # Filtrer les recettes par ingrédient
    recipes = (
        Recipe.query
        .join(IngredientQuantity)
        .join(Ingredient)
        .filter(Ingredient.name.ilike(f'%{ingredient_name}%'))
        .distinct(Recipe.id)
        .all()
    )

    # Construire la liste des recettes
    recipe_list = [{"name": recipe.name, "meal_type": recipe.meal_type.value} for recipe in recipes]

    return jsonify({"recipes": recipe_list})

def create_recipe():
    data = request.get_json()

    # Vérifier si la recette existe déjà
    existing_recipe = Recipe.query.filter(func.lower(Recipe.name) == func.lower(data['name'])).first()
    if existing_recipe:
        return jsonify({"error": "Erreur, cette recette est déjà présente dans la base de données"}), 400

    # Récupérer les informations sur les ingrédients de la recette
    ingredient_data = data.get('ingredients', [])

    # Vérifier et créer les ingrédients manquants avec leurs quantités
    ingredient_quantities = []
    for ingredient_info in ingredient_data:
        normalized_name = ingredient_info['name'].lower()
        existing_ingredient = Ingredient.query.filter(func.lower(Ingredient.name) == normalized_name).first()

        if not existing_ingredient:
            # Créer un nouvel ingrédient s'il n'existe pas
            new_ingredient = Ingredient(name=normalized_name)
            try:
                db.session.add(new_ingredient)
                db.session.commit()
                existing_ingredient = new_ingredient
            except IntegrityError:
                # En cas d'erreur d'intégrité (doublon), annuler la transaction
                db.session.rollback()
                existing_ingredient = Ingredient.query.filter(func.lower(Ingredient.name) == normalized_name).first()

        # Ajouter l'ingrédient à la liste avec la quantité
        ingredient_quantities.append(IngredientQuantity(
            ingredient=existing_ingredient,
            quantity=ingredient_info['quantity']
        ))

    # Créer la nouvelle recette
    new_recipe = Recipe(
        name=data['name'],
        ingredient_quantities=ingredient_quantities,
        steps=data.get('steps'),
        servings=data.get('servings'),
        meal_type=MealType(data.get('meal_type'))
    )

    # Ajouter la recette à la base de données
    db.session.add(new_recipe)
    
    try:
        db.session.commit()
    except IntegrityError:
        # En cas d'erreur d'intégrité (doublon), annuler la transaction
        db.session.rollback()
        return jsonify({"error": "Erreur lors de la création de la recette : ingrédient en double"}), 500

    return jsonify({"message": "Recipe created successfully"}), 201


@app.route('/users/<int:user_id>/recipes/<int:recipe_id>/favorite', methods=['POST', 'DELETE'])
def mark_or_remove_recipe_as_favorite(user_id, recipe_id):
    user = User.query.get_or_404(user_id)
    recipe = Recipe.query.get_or_404(recipe_id)

    if request.method == 'POST':
        # Ajouter la recette aux favoris de l'utilisateur
        existing_favorite = Favorite.query.filter_by(user=user, recipe=recipe).first()
        if existing_favorite:
            return jsonify({"error": "Cette recette est déjà dans vos favoris"}), 400

        favorite = Favorite(user=user, recipe=recipe)

        try:
            db.session.add(favorite)
            db.session.commit()
            return jsonify({"message": "Recipe marked as favorite successfully"}), 201
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Erreur lors de l'ajout de la recette aux favoris"}), 500

    elif request.method == 'DELETE':
        # Supprimer la recette des favoris de l'utilisateur
        existing_favorite = Favorite.query.filter_by(user=user, recipe=recipe).first()
        if existing_favorite:
            db.session.delete(existing_favorite)
            db.session.commit()
            return jsonify({"message": "Recette retirée des favoris avec succès"}), 200
        else:
            return jsonify({"error": "Cette recette n'est pas dans vos favoris"}), 404


@app.route('/users/<int:user_id>/favorites', methods=['GET'])
def get_user_favorites(user_id):
    user = User.query.get_or_404(user_id)
    favorites = Favorite.query.filter_by(user=user).all()
    favorite_recipes = [fav.recipe.name for fav in favorites]
    return jsonify({"user_id": user_id, "favorite_recipes": favorite_recipes, "username": user.username})

@app.route('/recipes/<int:recipe_id>/steps', methods=['GET'])
def get_recipe_steps(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return jsonify({"recipe_id": recipe_id, "steps": recipe.steps})



@app.route('/meals', methods=['POST'])
def create_meal():
    data = request.get_json()
    meal_type = MealType(data['type'])
    recipe_id = data['recipe_id']
    new_meal = Meal(type=meal_type, recipe_id=recipe_id)
    db.session.add(new_meal)
    db.session.commit()
    return jsonify({"message": f"{meal_type.value} created successfully"}), 201

@app.route('/menus', methods=['POST', 'GET'])
def manage_menus():
    if request.method == 'POST':
        return create_menu()
    elif request.method == 'GET':
        return get_all_menus()

# Fonction pour créer un menu
def create_menu():
    data = request.get_json()
    entree_id = data.get('entree_id')
    plat_id = data.get('plat_id')
    dessert_id = data.get('dessert_id')
    new_menu = Menu(name=data['name'], entree_id=entree_id, plat_id=plat_id, dessert_id=dessert_id)
    db.session.add(new_menu)
    db.session.commit()
    return jsonify({"message": "Menu created successfully"}), 201

# Fonction pour obtenir tous les menus
def get_all_menus():
    menus = Menu.query.all()
    menu_list = []
    for menu in menus:
        menu_dict = {
            "name": menu.name,
            "entree": get_meal_name(menu.entree_id) if menu.entree_id else None,
            "plat": get_meal_name(menu.plat_id) if menu.plat_id else None,
            "dessert": get_meal_name(menu.dessert_id) if menu.dessert_id else None
        }
        menu_list.append(menu_dict)
    return jsonify({"menus": menu_list})

# Fonction pour obtenir le nom du plat à partir de l'ID du repas
def get_meal_name(meal_id):
    meal = Meal.query.get(meal_id)
    return meal.type.value if meal and meal.type else None



@app.route('/ingredients/<int:servings>', methods=['GET'])
def get_ingredients_by_servings(servings):
    recipes = Recipe.query.filter_by(servings=servings).all()
    ingredients_list = set()
    for recipe in recipes:
        ingredients_list.update([ingredient.name for ingredient in recipe.ingredients])
    return jsonify({"ingredients": list(ingredients_list)})

@app.route('/recipes/<string:recipe_name>', methods=['GET'])
def get_recipe_details(recipe_name):
    # Rechercher la recette dans la base de données en utilisant le nom
    recipe = Recipe.query.filter(func.lower(Recipe.name) == func.lower(recipe_name)).first()

    if recipe:
        # Récupérer les informations sur les ingrédients avec quantités et unités
        ingredient_info_list = [
            {
                "name": iq.ingredient.name,
                "quantity": iq.quantity,
                "unit": iq.unit
            }
            for iq in recipe.ingredient_quantities
        ]

        recipe_details = {
            "name": recipe.name,
            "ingredients": ingredient_info_list,
            "steps": recipe.steps,
            "servings": recipe.servings,
            "meal_type": recipe.meal_type.value
        }

        return jsonify({"recipe": recipe_details})
    else:
        return jsonify({"error": f"Aucune recette trouvée avec le nom '{recipe_name}'"}), 404




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
