from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from enum import Enum

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    ingredients = db.relationship('Ingredient', secondary='recipe_ingredient', backref='recipes')
    steps = db.Column(db.Text, nullable=True)
    servings = db.Column(db.Integer, nullable=True)

recipe_ingredient = db.Table('recipe_ingredient',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
    db.Column('ingredient_id', db.Integer, db.ForeignKey('ingredient.id'), primary_key=True)
)

class MealType(Enum):
    ENTREE = "Entrée"
    PLAT = "Plat"
    DESSERT = "Dessert"

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

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201

@app.route('/ingredients', methods=['POST'])
def create_ingredient():
    data = request.get_json()
    new_ingredient = Ingredient(name=data['name'])
    db.session.add(new_ingredient)
    db.session.commit()
    return jsonify({"message": "Ingredient created successfully"}), 201

@app.route('/recipes', methods=['POST'])
def create_recipe():
    data = request.get_json()
    ingredients = Ingredient.query.filter(Ingredient.name.in_(data['ingredients'])).all()
    new_recipe = Recipe(
        name=data['name'],
        ingredients=ingredients,
        steps=data.get('steps'),  # Ajouter les étapes de préparation
        servings=data.get('servings')  # Ajouter le nombre de convives
    )
    db.session.add(new_recipe)
    db.session.commit()
    return jsonify({"message": "Recipe created successfully"}), 201

@app.route('/recipes', methods=['GET'])
def get_all_recipes():
    constraints = request.args.getlist('constraints')
    if constraints:
        ingredients = Ingredient.query.filter(Ingredient.name.in_(constraints)).all()
        recipes = Recipe.query.filter(Recipe.ingredients.contains(ingredients)).all()
    else:
        recipes = Recipe.query.all()

    recipe_list = []
    for recipe in recipes:
        recipe_list.append({
            'name': recipe.name,
            'ingredients': [ingredient.name for ingredient in recipe.ingredients],
            'steps': recipe.steps
        })

    return jsonify({"recipes": recipe_list})

@app.route('/users/<int:user_id>/recipes/<int:recipe_id>/favorite', methods=['POST'])
def mark_recipe_as_favorite(user_id, recipe_id):
    user = User.query.get_or_404(user_id)
    recipe = Recipe.query.get_or_404(recipe_id)
    favorite = Favorite(user=user, recipe=recipe)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"message": "Recipe marked as favorite successfully"}), 201

@app.route('/users/<int:user_id>/favorites', methods=['GET'])
def get_user_favorites(user_id):
    user = User.query.get_or_404(user_id)
    favorites = Favorite.query.filter_by(user=user).all()
    favorite_recipes = [fav.recipe.name for fav in favorites]
    return jsonify({"user_id": user_id, "favorite_recipes": favorite_recipes})

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

@app.route('/menus', methods=['POST'])
def create_menu():
    data = request.get_json()
    entree_id = data.get('entree_id')
    plat_id = data.get('plat_id')
    dessert_id = data.get('dessert_id')
    new_menu = Menu(name=data['name'], entree_id=entree_id, plat_id=plat_id, dessert_id=dessert_id)
    db.session.add(new_menu)
    db.session.commit()
    return jsonify({"message": "Menu created successfully"}), 201

@app.route('/ingredients/<int:servings>', methods=['GET'])
def get_ingredients_by_servings(servings):
    recipes = Recipe.query.filter_by(servings=servings).all()
    ingredients_list = set()
    for recipe in recipes:
        ingredients_list.update([ingredient.name for ingredient in recipe.ingredients])
    return jsonify({"ingredients": list(ingredients_list)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

