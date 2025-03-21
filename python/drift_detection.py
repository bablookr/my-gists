import numpy as np
import pandas as pd
from pyspark.sql import SparkSession
from scipy.stats import ks_2samp
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from ucimlrepo import fetch_ucirepo

"""
This implementation shows the detection of Data Drift and Concept Drift 
with the help of Credit Card Default dataset.

We use Apache Iceberg to store the snapshots of the dataset after adding 
artificial drift for both scenarios.

Once drift is detected, we retrain the Decision Tree classifier model on the 
new data including/excluding old data depending on the drift type. 
"""

np.random.seed(42)

CATALOG = "ml"
NAMESPACE = "credit_card_default"
TABLE_NAME = "test"


def fetch_data():
    dataset = fetch_ucirepo(name="Default of Credit Card Clients")

    X = dataset.data.features
    y = dataset.data.targets

    X = X.rename(
        columns={name: description for name, description in
                 zip(dataset.variables['name'], dataset.variables['description'])
                 if name not in ['ID', 'Y']}
    )
    y = y.rename(columns={'Y': 'default'})

    return X, y


class Evaluator():
    def __init__(self, spark):
        self.spark = spark

    def add_test_data(self, test_df, mode='create'):
        df = self.spark.createDataFrame(test_df)
        writer = df.writeTo(f"{CATALOG}.{NAMESPACE}.{TABLE_NAME}")
        if mode == 'create':
            writer.create()
        else:
            writer.replace()

    def validate(self, model, scaler):
        snapshots = self.read_snapshots()
        X_test, y_test = self.read_data(snapshots, 0)

        print("Testing on original dataset..")
        self.test(model, scaler, X_test, y_test)

    def read_snapshots(self):
        snapshots = self.spark.sql(f"SELECT * FROM {CATALOG}.{NAMESPACE}.{TABLE_NAME}.snapshots")
        return snapshots.collect()

    def read_data(self, snapshots, i):
        snapshot_id = snapshots[i]['snapshot_id']
        df = self.spark.sql(
            f"SELECT * FROM {CATALOG}.{NAMESPACE}.{TABLE_NAME} FOR VERSION AS OF {snapshot_id}").toPandas()
        feature_cols, target_col = df.columns[:-1], df.columns[-1]
        return df[feature_cols], df[target_col]

    def train(self, X_train, y_train):
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)

        model = DecisionTreeClassifier()
        model.fit(X_train_scaled, y_train)
        score = model.score(X_train_scaled, y_train)
        print("Training Accuracy:", score)

        return model, scaler

    def test(self, model, scaler, X_test, y_test):
        X_test_scaled = scaler.transform(X_test)
        score = model.score(X_test_scaled, y_test)
        print("Test Accuracy: ", score)


class DataDriftEvaluator(Evaluator):
    def __init__(self, spark):
        super().__init__(spark)

    def add_test_data(self, test_df, mode='replace'):
        test_df_copy = test_df.copy()
        test_df_copy['BILL_AMT1'] -= 10000
        test_df_copy['PAY_AMT1'] -= 10000
        super().add_test_data(test_df_copy, mode)

    def validate(self, model, scaler):
        snapshots = self.read_snapshots()
        X_test, y_test = self.read_data(snapshots, 0)
        X_test_drifted, y_test = self.read_data(snapshots, 1)

        print("\nTesting on dataset with data drift..")
        self.test(model, scaler, X_test_drifted, y_test)

        drift_detected = self.check_for_drift(X_test, X_test_drifted)
        print("Data Drift Detected:", drift_detected)

        if drift_detected:
            print("Retraining on a mixture of old data and new data..")
            X_sampled, y_sampled = X.sample(frac=0.3), y.loc[X.sample(frac=0.3).index]
            X_retrain = pd.concat([X_sampled, X_test_drifted])
            y_retrain = pd.concat([y_sampled, y_test])
            self.train(X_retrain, y_retrain)

    def check_for_drift(self, X_test, X_test_drifted, threshold=0.05):
        drift_detected = False
        for column in X_test.columns:
            stat, p_value = ks_2samp(X_test[column], X_test_drifted[column])
            if p_value < threshold:
                drift_detected = True
                break

        return drift_detected


class ConceptDriftEvaluator(Evaluator):
    def __init__(self, spark):
        super().__init__(spark)

    def add_test_data(self, test_df, mode='replace'):
        test_df_copy = test_df.copy()
        test_df_copy['default'] = test_df_copy['default'].apply(lambda x: 1 if np.random.rand() < 0.2 else x)
        super().add_test_data(test_df_copy, mode)

    def validate(self, model, scaler, ):
        snapshots = self.read_snapshots()
        X_test, y_test = self.read_data(snapshots, 0)
        X_test, y_test_drifted = self.read_data(snapshots, 2)

        print("\nTesting on dataset with concept drift..")
        self.test(model, scaler, X_test, y_test_drifted)

        drift_detected = self.check_for_drift(y_test, y_test_drifted)
        print("Concept Drift Detected:", drift_detected)

        if drift_detected:
            print("Retraining on new data..")
            self.train(X_test, y_test_drifted)

    def check_for_drift(self, y_test, y_test_drifted, threshold=0.2):
        y_test_dist = y_test.value_counts(normalize=True)
        y_test_drifted_dist = y_test_drifted.value_counts(normalize=True)

        tvd = sum(abs(y_test_dist - y_test_drifted_dist).fillna(0))
        return tvd > threshold


if __name__ == '__main__':
    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("DriftEvaluator") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.8.1") \
        .config(f"spark.sql.catalog.{CATALOG}", "org.apache.iceberg.spark.SparkCatalog") \
        .config(f"spark.sql.catalog.{CATALOG}.type", "hadoop") \
        .config(f"spark.sql.catalog.{CATALOG}.warehouse", "/tmp/warehouse") \
        .getOrCreate()

    try:
        X, y = fetch_data()
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
        train_df = pd.concat([X_train, y_train], axis=1)
        test_df = pd.concat([X_test, y_test], axis=1)

        evaluator = Evaluator(spark)
        print("Training on original dataset..")
        model, scaler = evaluator.train(X_train, y_train)

        evaluator.add_test_data(test_df)
        evaluator.validate(model, scaler)

        data_drift_evaluator = DataDriftEvaluator(spark)
        data_drift_evaluator.add_test_data(test_df)
        data_drift_evaluator.validate(model, scaler)

        concept_drift_evaluator = ConceptDriftEvaluator(spark)
        concept_drift_evaluator.add_test_data(test_df)
        concept_drift_evaluator.validate(model, scaler)

    except Exception as e:
        print(f"An error occurred while running the evaluator: {e}")
        raise e

    finally:
        spark.stop()
