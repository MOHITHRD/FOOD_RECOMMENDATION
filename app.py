from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from model.model import predict  # Importing your prediction function
import time
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin # For login authentication


# For Edamam API Key .env loading
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables
EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY")
EDAMAM_ACCOUNT_USER = os.getenv("EDAMAM_ACCOUNT_USER")


app = Flask(__name__)


# Initializing flask login 
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirects unauthenticated users to login page


# Secret key for handling sessions and all
app.secret_key = 'RDMohith@172003'


# For database
from flask_sqlalchemy import SQLAlchemy
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Avoids unnecessary warnings


db = SQLAlchemy(app)  # Initialize the database


# Users Table (Stores user_id and password)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique User ID
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)  # Store hashed password
    # Function to set password securely
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    # Function to verify password during login
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# User Data Table (Stores user profile details)
class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Links to Users Table
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)


# Predictions Table (Stores predictions for each user)
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Links to Users Table
    age = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    inactivity_hours = db.Column(db.Float, nullable=False)
    proteins = db.Column(db.Float, nullable=False)
    carbohydrates = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)


# hashing password for security and authentication
from werkzeug.security import generate_password_hash, check_password_hash


# Function so that Flask-Login can retreive users
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Home Route - Display the input form
@app.route('/')
def home():
    return redirect(url_for('signup'))
    

# Sign up route - Handles sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists! Choose a different one.', 'danger')
            return redirect(url_for('signup'))

        # Create a new user
        new_user = User(username=username)
        new_user.set_password(password)  # Hash the password before storing
        db.session.add(new_user)
        db.session.commit()

        flash('Signup successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


# Login route - handles login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if user exists
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # Verify password
            login_user(user)  # Log in user
            flash('Login successful!', 'success')
            return redirect(url_for('profile'))  # Redirect to profile/dashboard

        flash('Invalid username or password', 'danger')

    return render_template('login.html')


# Profile route - handles profile
@app.route('/profile', methods=['GET', 'POST'])
@login_required  # Ensures only logged-in users can access this page
def profile():
    user_data = UserData.query.filter_by(user_id=current_user.id).first()

    # BMI variables initialization
    bmi = None
    bmi_category = None
    ideal_weight_min = None
    ideal_weight_max = None

    if user_data:
        bmi, bmi_category, ideal_weight_min, ideal_weight_max = calculate_bmi(user_data.weight, user_data.height)

    # Initialize filter variables
    diet_label = None
    cuisine = None
    meal = None
    dish = None
    exclude = []
    vegetarian = False

    if request.method == 'POST':
        if 'update_profile' in request.form:  # If user clicks "Update Profile"
            name = request.form['name']
            age = int(request.form['age'])
            sex = request.form['sex']
            weight = float(request.form['weight'])
            height = float(request.form['height'])

            if user_data:  # If profile exists, update it
                user_data.name = name
                user_data.age = age
                user_data.sex = sex
                user_data.weight = weight
                user_data.height = height
            else:  # If no profile exists, create a new one
                user_data = UserData(
                    user_id=current_user.id,
                    name=name,
                    age=age,
                    sex=sex,
                    weight=weight,
                    height=height
                )
                db.session.add(user_data)

            db.session.commit()

            # BMI (If profile is new)
            bmi, bmi_category, ideal_weight_min, ideal_weight_max = calculate_bmi(weight, height)

        elif 'apply_filters' in request.form:  # Apply Filters button clicked
            print("DEBUG: Full Form Data Received ->", request.form)  # 🛠 Debug print

            # Extract filter values (None if not selected)
            diet_label = request.form.get('diet_label', None) or None
            cuisine = request.form.get('cuisine', None) or None
            meal = request.form.get('meal', None) or None
            dish = request.form.get('dish', None) or None
            exclude = request.form.getlist('exclude')  # List of excluded ingredients
            vegetarian = 'vegetarian' in request.form  # Boolean check

            flash("Filters applied successfully!", "success")

        elif 'predict' in request.form:  # If user clicks "Predict"
            inactivity_hours = float(request.form['inactivity_hours'])

            if user_data:  # Ensure profile exists before predicting
                result = predict(user_data.age, user_data.weight, user_data.height, user_data.sex, inactivity_hours)
                
                # Fetch food suggestion from Edamam API
                food_suggestion = get_food_suggestion(
                    result['proteins'],
                    result['carbohydrates'],
                    result['calories'],
                    diet_label=diet_label,
                    cuisine=cuisine,
                    meal=meal,
                    dish=dish,
                    exclude=exclude,
                    vegetarian=vegetarian
                )

                # Store prediction in Predictions Table
                prediction = Prediction(
                    user_id=current_user.id,
                    age=user_data.age,
                    height=user_data.height,
                    weight=user_data.weight,
                    sex=user_data.sex,
                    inactivity_hours=inactivity_hours,
                    proteins=result['proteins'],
                    carbohydrates=result['carbohydrates'],
                    calories=result['calories']
                )
                db.session.add(prediction)
                db.session.commit()

                flash("Prediction successful!", "success")
                return render_template('result.html', proteins=result['proteins'], carbs=result['carbohydrates'], calories=result['calories'], food_suggestions=food_suggestion)
            else:
                flash("Please complete your profile before making a prediction.", "danger")

    return render_template('profile.html', user_data=user_data, bmi=bmi, bmi_category=bmi_category, 
                           ideal_weight_min=ideal_weight_min, ideal_weight_max=ideal_weight_max,
                           diet_label=diet_label, cuisine=cuisine, meal=meal, dish=dish, exclude=exclude,
                           vegetarian=vegetarian)


# Logout route - handles logout
@app.route('/logout')
@login_required
def logout():
    logout_user()  # Logs out the user
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))  # Redirect to login page


#Query Edamam API and display result
import requests
def get_food_suggestion(proteins, carbs, calories, diet_label=None, cuisine=None, meal=None, dish=None, exclude=None, vegetarian=False):
    url = "https://api.edamam.com/api/recipes/v2"
    time.sleep(5)  
    params = {
        'app_id': EDAMAM_APP_ID,
        'app_key': EDAMAM_APP_KEY,
        'type': 'public',
        'nutrients[PROCNT]': f"{round(proteins * 0.8, 2)}-{round(proteins * 1.2, 2)}",    
        'nutrients[CHOCDF]': f"{round(carbs * 0.8, 2)}-{round(carbs * 1.2, 2)}",       
        'nutrients[ENERC_KCAL]': f"{round(calories * 0.85, 2)}-{round(calories * 1.15, 2)}",
        'to': 10  # Return only 10 food items
    }

    # Apply filters if they are selected
    if diet_label:
        params['diet'] = diet_label
    if cuisine:
        params['cuisineType'] = cuisine
    if meal:
        params['mealType'] = meal
    if dish:
        params['dishType'] = dish
    if exclude:
        params['excluded'] = exclude  # Exclude ingredients
    if vegetarian:  #  Apply vegetarian filter if checkbox is checked
        params['health'] = 'vegetarian'

    
    headers = {
        'Edamam-Account-User': EDAMAM_ACCOUNT_USER  # Add this header back
    }

    #print("Request URL:", url)
    #print("Request Parameters:", params)
    #print("Request Headers:", headers)
    response = requests.get(url, params=params,headers=headers)
    #print("Response Status Code:", response.status_code)
    #print("Response Content:", response.text[:1000])  # Shows the full response for inspection

    if response.status_code == 200:
        data = response.json()
        if 'hits' in data and data['hits']:
            food_list = []
            for hit in data['hits']:
                recipe = hit['recipe']

                # Calculate how close the match is
                protein_diff = abs(recipe['totalNutrients']['PROCNT']['quantity'] - proteins)
                carb_diff = abs(recipe['totalNutrients']['CHOCDF']['quantity'] - carbs)
                calorie_diff = abs(recipe['calories'] - calories)
                total_diff = protein_diff + carb_diff + calorie_diff  # Total deviation

                food_list.append({
                    "name": recipe['label'],
                    "url": recipe['url'],
                    "calories": round(recipe['calories']),
                    "proteins": round(recipe['totalNutrients']['PROCNT']['quantity'], 2),
                    "carbohydrates": round(recipe['totalNutrients']['CHOCDF']['quantity'], 2),
                    "fats": round(recipe['totalNutrients']['FAT']['quantity'], 2),
                    "ingredients": recipe['ingredientLines'],
                    "diet_labels": recipe['dietLabels'],
                    "cuisine_type": recipe.get('cuisineType', ['N/A'])[0],
                    "meal_type": recipe.get('mealType', ['N/A'])[0],
                    "dish_type": recipe.get('dishType', ['N/A'])[0],
                    "image": recipe.get('image'),  # Main recipe image if available
                    "diff": total_diff  # Store how far it is from the target values
                })
            food_list = sorted(food_list, key=lambda x: x["diff"])
            return food_list
        else:
            return []
    else:
        return []


# Function to calculate BMI, BMI category, and ideal weight range
def calculate_bmi(weight, height_cm):
    height_m = height_cm / 100  # Convert cm to meters
    bmi = round(weight / (height_m ** 2), 2)

    # Determine BMI category
    if bmi < 18.5:
        bmi_category = "Underweight"
    elif 18.5 <= bmi < 24.9:
        bmi_category = "Normal weight"
    elif 25 <= bmi < 29.9:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"

    # Ideal weight range based on BMI 18.5 - 24.9
    ideal_weight_min = round(18.5 * (height_m ** 2), 1)
    ideal_weight_max = round(24.9 * (height_m ** 2), 1)

    return bmi, bmi_category, ideal_weight_min, ideal_weight_max


# Run the Flask app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates database tables if they don't exist
    print("Database and tables created successfully!")
    app.run(debug=True)
