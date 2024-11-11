import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.decomposition import PCA
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


class PCA_Manager:
    def __init__(self):
        pass

    def convert_x_to_pca(self, x, numeric_features, categorical_features): #90 components exactly
        X = x
        X[numeric_features] = X[numeric_features].fillna(X[numeric_features].mean())

        for cat_feature in categorical_features:
            X[cat_feature] = X[cat_feature].fillna('Unknown')
            X[cat_feature] = X[cat_feature].astype(str)
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', Pipeline([
                    ('scaler', StandardScaler())
                ]), numeric_features),
                ('cat', Pipeline([
                    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
                ]), categorical_features)
            ],
            remainder='drop'
        )

        pca_pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('pca', PCA(n_components=90))
            ])

        return pca_pipeline.fit_transform(X)