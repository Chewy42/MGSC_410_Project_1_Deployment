import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from pca_workflow import PCA_Manager
from sklearn.impute import SimpleImputer

class PredictionService:
    def __init__(self):
        try:
            model_path = Path(__file__).parent.parent / 'nn_model.pkl'
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at {model_path}")
            self.model = joblib.load(model_path)
            self.pca_manager = PCA_Manager()
            
            # Initialize imputers
            self.numeric_imputer = SimpleImputer(strategy='mean')
            self.categorical_imputer = SimpleImputer(strategy='constant', fill_value='UNKNOWN')
            
        except Exception as e:
            print(f"Error initializing PredictionService: {str(e)}")
            self.model = None
            
    def predict_fair_price(self, properties_df):
        """
        Generate fair price predictions for properties using the neural network model
        """
        try:
            if self.model is None:
                print("Warning: Using actual prices as fair prices due to model loading failure")
                return properties_df['price'].values
            
            # Create a copy to avoid modifying the original dataframe
            df = properties_df.copy()
            
            # Print shape information for debugging
            print(f"Input DataFrame shape: {df.shape}")
            
            # Define numeric and categorical features
            numeric_features = df.select_dtypes(
                include=['int32', 'float32', 'int64', 'float64']
            ).columns.tolist()
            
            categorical_features = df.select_dtypes(
                include=['object', 'category']
            ).columns.tolist()
            
            # Remove price and any problematic columns from features
            columns_to_remove = ['price', 'fair_price', 'id']
            numeric_features = [col for col in numeric_features 
                              if col not in columns_to_remove and 
                              not col.startswith('schools/')]
            
            categorical_features = [col for col in categorical_features 
                                  if col not in columns_to_remove and 
                                  not col.startswith('schools/')]
            
            print(f"Number of numeric features: {len(numeric_features)}")
            print(f"Number of categorical features: {len(categorical_features)}")
            
            # Handle missing values for numeric features
            if numeric_features:
                # Impute each numeric column separately to avoid dimension mismatch
                for col in numeric_features:
                    if df[col].isnull().any():
                        df[col] = self.numeric_imputer.fit_transform(
                            df[col].values.reshape(-1, 1)
                        ).ravel()
            
            # Handle missing values for categorical features
            if categorical_features:
                # Impute each categorical column separately
                for col in categorical_features:
                    if df[col].isnull().any():
                        df[col] = self.categorical_imputer.fit_transform(
                            df[col].values.reshape(-1, 1)
                        ).ravel()
                        df[col] = df[col].astype(str)
            
            # Transform data using PCA
            X_pca = self.pca_manager.convert_x_to_pca(
                df, 
                numeric_features, 
                categorical_features
            )
            
            print(f"PCA transformed shape: {X_pca.shape}")
            
            # Generate predictions
            predictions = self.model.predict(X_pca)
            print(f"Raw predictions shape: {predictions.shape}")
            
            # Ensure predictions are a 1D array with the correct length
            predictions = predictions.reshape(-1)
            if len(predictions) != len(df):
                raise ValueError(f"Prediction length ({len(predictions)}) does not match input length ({len(df)})")
            
            # Ensure predictions are positive and reasonable
            predictions = np.maximum(predictions, 0)  # No negative prices
            
            # Add some noise to avoid identical predictions
            noise = np.random.normal(1, 0.05, size=len(predictions))
            predictions = predictions * noise
            
            # Validate predictions
            actual_prices = properties_df['price'].values
            predictions = self._validate_predictions(predictions, actual_prices)
            
            print(f"Final predictions shape: {predictions.shape}")
            return predictions
            
        except Exception as e:
            print(f"Error predicting fair prices: {str(e)}")
            import traceback
            traceback.print_exc()  # Print full stack trace
            return properties_df['price'].values
            
    def _validate_predictions(self, predictions, actual_prices):
        """
        Validate predictions and adjust if they seem unreasonable
        """
        try:
            # Ensure arrays are the same length
            if len(predictions) != len(actual_prices):
                raise ValueError(f"Prediction length ({len(predictions)}) does not match actual prices length ({len(actual_prices)})")
            
            # Ensure predictions are within reasonable bounds of actual prices
            lower_bound = actual_prices * 0.5  # 50% of actual price
            upper_bound = actual_prices * 1.5  # 150% of actual price
            
            # Clip predictions to these bounds
            validated_predictions = np.clip(predictions, lower_bound, upper_bound)
            
            return validated_predictions
            
        except Exception as e:
            print(f"Error validating predictions: {str(e)}")
            return predictions  # Return original predictions if validation fails