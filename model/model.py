import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model #type: ignore
import joblib  # For loading scalers


# Load the trained model
model = tf.keras.models.load_model('model/trained_model.keras')


# Load the saved scalers
scaler_x = joblib.load('model/scaler_x.pkl')
scaler_y = joblib.load('model/scaler_y.pkl')


# Prediction function
def predict(age, weight, height, sex, inactivity_hours):
    # Encode 'sex' (0 for Female, 1 for Male)
    sex_encoded = 0 if sex.lower() == 'f' else 1  

    # Prepare the input array
    input_data = np.array([[age, sex_encoded, weight, height, inactivity_hours]])

    # Scale the input data
    input_scaled = scaler_x.transform(input_data)

    # Make predictions
    prediction = model.predict(input_scaled)

    # Inverse scaling for predictions
    prediction_unscaled = scaler_y.inverse_transform(prediction)

    # Extract predicted values
    predicted_proteins, predicted_carbs, predicted_calories = prediction_unscaled[0]

    return {
        "proteins": round(predicted_proteins, 2),
        "carbohydrates": round(predicted_carbs, 2),
        "calories": round(predicted_calories, 2)
    }
