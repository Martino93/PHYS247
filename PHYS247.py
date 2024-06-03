import pandas as pd
import numpy as np

from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.feature_selection import RFE

from sklearn.linear_model import LogisticRegression
from sklearn.linear_model import Lasso
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier

from sklearn.ensemble import RandomForestClassifier

from sklearn.tree import DecisionTreeClassifier

from scipy.sparse import csr_matrix
import xgboost as xgb

from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, log_loss

# import plotly.express as px

from feature_engine.selection import DropDuplicateFeatures, DropCorrelatedFeatures

# Display all columns
pd.set_option('display.max_columns', None)



class DataProcessor():
    
    def __init__(self, path):
        
        self.path = path
        
        # get test data.
        test_path = self.path.replace('train', 'test')
        
        self.df_test = pd.read_csv(test_path)                
        self.df_train = pd.read_csv(path)
                        
        self.X_train = np.array([])
        self.Y_train = np.array([])
        self.X_test = np.array([])
        self.Y_test = np.array([])
        
        self.scaled_X_train = np.array([])
        self.scaled_Y_test = np.array([])

    def clean_data(self):

        # drop duplicate rows
        self.df_clean = self.df_train.drop_duplicates()
        print("Dropped", self.df_train.shape[0] - self.df_clean.shape[0], "duplicate records")

        #Percentage of satified customers
        counts = self.df_clean['TARGET'].value_counts()
        satisfied_percentage = counts.loc[0]/len(self.df_clean) * 100
        print("The given dataset is larger skewed towards satified customers showing a", satisfied_percentage,"percent observation")   

        self.drop_columns()
        
        # plot the distribution of customer satisfaction
        plt.bar(counts.index, counts.values)
        plt.xlabel('Customer Satisfaction')
        plt.ylabel('Count')
        plt.title('Customer Satisfaction Distribution')
        plt.xticks(counts.index, labels = ['Satisfied', 'Dissatisfied'])
        plt.show()
  

    def drop_columns(self):
        # drop columns where all values are the same.
        constant_columns = []
        # Loop through columns in the dataset to check whether they contain unique values
        for column in self.df_clean.columns:
            if self.df_clean[column].nunique() <= 1:
                #Add column name to list if no unique values are present
                constant_columns.append(column)
            
        print(f'Remove {len(constant_columns)} columns with constant values')
        self.df_clean = self.df_clean.drop(columns=constant_columns)

        # Dropping Duplicate Columns
        duplicates = DropDuplicateFeatures()
        duplicates.fit(self.df_clean)
        duplicates.duplicated_feature_sets_

        print('Number of columns before removing the duplicates is:', self.df_clean.shape[1])
        self.df_clean = duplicates.transform(self.df_clean)
        print('Number of columns after removing the duplicates is:', self.df_clean.shape[1])        


    def feature_cols(self):
        other = ['ID', 'TARGET']
        return [col for col in self.df_train.columns if col not in other]


    def partition_data(self):
        target_train = self.df_train['TARGET'].values
        features_train = self.df_train.drop(columns=['ID', 'TARGET']).values

        # split the train data since the test dataset is missing the target column
        self.X_train, self.X_test, self.Y_train, self.Y_test = train_test_split(
            features_train,
            target_train,
            test_size=0.2,
            shuffle=True,
            random_state=42
            )
        print('Train data shape:', self.X_train.shape)
        print('Test data shape:', self.X_test.shape)
        
        
    def scale_features(self):
        scaler = StandardScaler()
        self.scaled_X_train = scaler.fit_transform(self.X_train)
        self.scaled_X_test = scaler.fit_transform(self.X_test)

        return self.scaled_X_train, self.Y_train, self.scaled_X_test, self.Y_test
        
   

class DataVisualizer():
    
    def __init__(self, model_performance:dict):
        self.scaled_features_df_reduced = pd.DataFrame()
        self.model_performance = model_performance      

        
    def plot_model_performance(self):
        df = pd.DataFrame(self.model_performance).T
        
        # normalize log loss
        df['log_loss'] = 1 - df['log_loss'] / df['log_loss'].max()
        
        fig = px.line_polar(df.reset_index().melt(id_vars='index'), 
                            r='value', theta='variable', color='index', line_close=True,
                            title='Model Performance Metrics')

        fig.update_traces(fill='toself')
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            )
        )

        fig.show()        
        
    def create_correlation_matrix(self, threshold=0.5):
        df = self.df.corr().abs()
        # Select upper triangle of correlation matrix
        upper = df.where(np.triu(np.ones(df.shape), k=1).astype(bool))
        
        # Find index of feature columns with correlation greater than 0.9
        to_drop = [column for column in upper.columns if any(upper[column] > 0.9)]

        # Drop features 
        self.scaled_features_df_reduced = upper.drop(columns=to_drop)        
        return self.scaled_features_df_reduced
    

    def make_heatmap(self, values, cols, threshold=0.5):      

        plt.figure(figsize=(20, 20))

        plt.title('Correlation Matrix of Scaled Features')
        sns.heatmap(
            self.scaled_features_df_reduced, 
            annot=True, 
            fmt='.2f', 
            cmap='coolwarm', 
            vmin=-1, 
            vmax=1, 
            linewidths=0, 
            square=True
        )

        plt.show()
    
    def confusion_matrix(self):
        confusion_matrix_list = []

        for i in self.model_performance.keys():
            confusion_matrix_list.append(confusion_matrix(self.model_performance[i]['y_true'], self.model_performance[i]['prediction']))

        fig, ax = plt.subplots(2, 3, figsize=(20, 10))

        for i, ax in enumerate(ax.flat):
            sns.heatmap(confusion_matrix_list[i], annot=True, fmt='d', cmap='Blues', ax=ax)
            ax.set_title(list(self.model_performance.keys())[i])
            ax.set_xlabel('Predicted')
            ax.set_ylabel('Actual')
            ax.set_xticklabels(['Satisfied', 'Dissatisfied'])
            ax.set_yticklabels(['Satisfied', 'Dissatisfied'])

        plt.tight_layout()
        plt.show()



class FeatureSelector():
    def __init__(self, X_df, Y_df):
        self.X_df = X_df
        self.Y_df = Y_df
        self.selected_features_df = pd.DataFrame()
        
        self.X_new = pd.DataFrame()
                
    
    def correlation_based_selection(self, threshold=0.9):
        # Calculate correlation matrix
        corr_matrix = self.X_df.corr().abs()

        # Select upper triangle of correlation matrix
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

        # Find index of feature columns with correlation greater than threshold
        to_drop = [column for column in upper.columns if any(upper[column] > threshold)]

        # Drop features 
        self.X_new = self.X_df.drop(columns=to_drop)
        
        
    def univariate_selection(self, num_features):
        selector = SelectKBest(score_func=f_classif, k=num_features)
        self.X_new = selector.fit_transform(self.X_df, self.Y_df)
        self.selected_features_df = self.X_df.columns[selector.get_support()]

 def execute_rfe(self):
        x_train_scaled_sparse = csr_matrix(self.scaled_X_train)
        x_test_scaled_sparse = csr_matrix(self.scaled_X_test)
        model = LogisticRegression(max_iter=1000, random_state=0, solver='saga')
        rfe = RFE(estimator=model, n_features_to_select=self.n_features_to_select)
        rfe.fit(x_train_scaled_sparse, self.Y_train)
        x_train_rfe = rfe.transform(x_train_scaled_sparse)
        x_test_rfe = rfe.transform(x_test_scaled_sparse)
        #Acquiring selected features
        selected_features_rfe = self.df_clean.drop(columns=['ID', 'TARGET']).columns[rfe.support_]
        print("Selected features:", selected_features_rfe)
         # Converting back to DataFrame
        self.x_train_rfe = pd.DataFrame(x_train_rfe.toarray(), columns=selected_features_rfe)
        self.x_test_rfe = pd.DataFrame(x_test_rfe.toarray(), columns=selected_features_rfe)
        return self.x_train_rfe, self.Y_train, self.x_test_rfe, self.Y_test
    
   # def recursive_feature_elimination(self):
        #model = LogisticRegression()
        #rfe = RFE(model, 10, step = 1)
        #rfe.fit(self.X_df, self.Y_df)
        #self.X_new = rfe.transform(self.X_df)
        
    def random_forest_selection(self):
        model = RandomForestClassifier()
        model.fit(self.X_df, self.Y_df)
        self.X_new = model.feature_importances_
        self.selected_features_df = self.X_df.columns[model.get_support()]
        
        # Sort by importance
        feature_importances = feature_importances.sort_values(by='importance', ascending=False)

        # Select top features
        selected_features = feature_importances['feature'].head(10)
        
    def lasso_selection(self):
        

        # Initialize the model with L1 regularization
        model = Lasso(alpha=0.1)

        # Fit the model
        model.fit(self.X_df, self.Y_df)

        # Get coefficients
        coefficients = model.coef_

        # Create a DataFrame with feature names and their coefficients
        feature_coefficients = pd.DataFrame({'feature': self.X_df.columns, 'coefficient': coefficients})

        # Select non-zero coefficients
        selected_features = feature_coefficients[feature_coefficients['coefficient'] != 0]['feature']


          
class MLModel():
    def __init__(self, X_train, Y_train, X_test, Y_test):
        self.X_train = X_train
        self.Y_train = Y_train
        self.X_test = X_test
        self.Y_test = Y_test  
              
        self.model = None
        self.prediction = None
        self.accuracy = None
        
        self.model_performance = defaultdict()

    def assess_model(self, model:str):
        print(f'Assessing {model} model')
        self.prediction = self.model.predict(self.X_test)
        self.accuracy = self.model.score(self.X_test, self.Y_test)
        
        self.precision = precision_score(self.Y_test, self.prediction)
        self.recall = recall_score(self.Y_test, self.prediction)
        self.f1 = f1_score(self.Y_test, self.prediction)
        self.roc_auc = roc_auc_score(self.Y_test, self.prediction)
        self.log_loss = log_loss(self.Y_test, self.prediction)
        self.classification_report = classification_report(self.Y_test, self.prediction)
        
        self.model_performance[model] = {
            'y_true': self.Y_test,
            'prediction': self.prediction,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1': self.f1,
            'roc_auc': self.roc_auc,
            'log_loss': self.log_loss,
            'classification_report': self.classification_report
        }
               

    def logistic_regression(self):
        self.model = LogisticRegression(solver='liblinear', random_state=0)
        self.model = self.model.fit(self.X_train, self.Y_train)
        
        self.assess_model(model='logistic_regression')
        
        
    def random_forest(self):
        self.model = RandomForestClassifier()
        self.model = self.model.fit(self.X_train, self.Y_train)
        
        self.assess_model(model='random_forest')      

    def decision_tree(self):
        self.model = DecisionTreeClassifier()
        self.model = self.model.fit(self.X_train, self.Y_train)
        
        self.assess_model(model='decision_tree')
        
    def xgboost(self):
        self.model = xgb.XGBClassifier()
        self.model.fit(self.X_train, self.Y_train)
        
        self.assess_model(model='xgboost')
        
    def svm(self):
        self.model = SVC(probability=True)
        self.model.fit(self.X_train, self.Y_train)
        
        self.assess_model(model='svm')
        
    def neural_network(self):
        self.model = MLPClassifier()
        self.model.fit(self.X_train, self.Y_train)
        
        self.assess_model(model='neural_network')
    
    







# ---------------------
# FEATURE SELECTION
# Selector = FeatureSelector(scaled_X_df, Y_df)


# correlation based selection
# Selector.correlation_based_selection()
# X_new = Selector.scaled_X_filtered_df
# # univariate selection
# X_new = Selector.univariate_selection(num_features=10)
# # recursive feature elimination
# X_new = Selector.recursive_feature_elimination()
# # random forest selection
# X_new = Selector.random_forest_selection()
# # lasso selection
# X_new = Selector.lasso_selection()






# visualize the data
# ---------------------

# display correlation heatmap
# Visualizer = DataVisualizer()
# corr_arr = Visualizer.create_correlation_matrix()
# Visualizer.make_heatmap(corr_arr, Processor.feature_cols())





# ---------------------
# evaluate the models
## cross validation
## evaluate probabilistic predictions

# ---------------------
# tune the models
## grid search
## random search
## bayesian optimization

# ---------------------
# stack the models
# use shap values to explain the model

# ---------------------
# Compare the models
