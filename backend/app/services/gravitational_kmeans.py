import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import numpy as np
import pandas as pd
from typing import Optional
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix
# from tensorflow.keras import Input  # type: ignore
# from tensorflow.keras.models import Sequential  # type: ignore
# from tensorflow.keras.layers import Dense  # type: ignore
# from tensorflow.keras.optimizers import Adam  # type: ignore
from keras import Input 
from keras.models import Sequential 
from keras.layers import Dense
from keras.optimizers import Adam
from app.services.processing.interval_divider import IntervalDivider
from app.services.processing.grid_merger import GridMerger
from app.services.processing.grid_processor import GridProcessor

class GravitationalKMeans:
    """
    Implements a gravitational-based K-Means clustering algorithm with label-based force adjustments.
    """

    def __init__(self, data: pd.DataFrame, initial_clusters: list, enhancement_factor: float = 0, max_iterations: int = 100, eval_every: int = 3, eval_stop_at: Optional[int] = None):
        """
        Initializes the GravitationalKMeans class with dataset and initial clusters.

        Args:
            data (pd.DataFrame): DataFrame containing the data to cluster (last column is assumed to be labels).
            initial_clusters (list of lists): List of initial sample indices for each cluster.
            enhancement_factor (float): Factor to adjust the gravitational force based on label matching.
            max_iterations (int): Maximum number of iterations for the algorithm.
        """
        self.data = data
        self.features = self.data.iloc[:, :-1].to_numpy()  # Features excluding the last column (assumed to be labels)
        self.labels = self.data.iloc[:, -1].to_numpy()  # Labels are in the last column
        self.initial_clusters = initial_clusters
        self.enhancement_factor = enhancement_factor
        self.max_iterations = max_iterations
        self.centroids = np.array([self.features[indices].mean(axis=0) for indices in initial_clusters])
        self.weights = np.array([len(indices) for indices in initial_clusters])
        self.dominant_labels = np.array([np.bincount(self.labels[indices]).argmax() for indices in initial_clusters])
        self.accuracy_history = []
        self.max_avg_accuracy = 0
        self.best_clusters = []
        self.eval_every = eval_every
        self.eval_stop_at = eval_stop_at

    def fit(self):
        """
        Performs the clustering process using gravitational force with label-based force adjustment.
        """
        for _ in range(self.max_iterations):
            new_clusters = [[] for _ in range(len(self.initial_clusters))]
            for i in range(len(self.features)):
                distances = np.linalg.norm(self.features[i] - self.centroids, axis=1)
                forces = self.weights / np.square(distances)
                label = self.labels[i]
                for j, centroid_label in enumerate(self.dominant_labels):
                    forces[j] *= (1 + self.enhancement_factor) if label == centroid_label else (1 - self.enhancement_factor)
                cluster_index = np.argmax(forces)
                new_clusters[cluster_index].append(i)

            # Update centroids, weights, and dominant labels based on new clusters
            self.centroids = np.array([self.features[indices].mean(axis=0) for indices in new_clusters])
            self.weights = np.array([len(indices) for indices in new_clusters])
            self.dominant_labels = np.array([np.bincount(self.labels[indices]).argmax() for indices in new_clusters])

    def fit_incremental(self):
        """
        Incrementally assigns samples to clusters based on gravitational force.
        """
        clusters = [list(cluster) for cluster in self.initial_clusters]
        all_samples_indices = set(range(len(self.features)))
        initial_samples_indices = set(idx for cluster in self.initial_clusters for idx in cluster)
        remaining_samples_indices = all_samples_indices - initial_samples_indices
        sample_counter = 0

        while remaining_samples_indices:
            max_force = -np.inf
            selected_sample_index = None
            selected_cluster_index = None

            for sample_index in remaining_samples_indices:
                for cluster_index, (centroid, weight, dominant_label) in enumerate(
                        zip(self.centroids, self.weights, self.dominant_labels)):
                    distance = np.linalg.norm(self.features[sample_index] - centroid)
                    distance = max(distance, 1e-10)  # Avoid division by zero
                    force = weight / distance ** 2
                    force *= (1 + self.enhancement_factor) if self.labels[sample_index] == dominant_label else (1 - self.enhancement_factor)

                    if force > max_force:
                        max_force = force
                        selected_sample_index = sample_index
                        selected_cluster_index = cluster_index

            clusters[selected_cluster_index].append(selected_sample_index)
            remaining_samples_indices.remove(selected_sample_index)
            sample_counter += 1

            if self.eval_every and (sample_counter % self.eval_every == 0 or not remaining_samples_indices):
                if self.eval_stop_at is None or sample_counter <= self.eval_stop_at:
                    self.evaluate_accuracy(clusters)

            # Update centroids, weights, and dominant labels
            self.centroids[selected_cluster_index] = self.features[clusters[selected_cluster_index]].mean(axis=0)
            self.weights[selected_cluster_index] = len(clusters[selected_cluster_index])
            self.dominant_labels[selected_cluster_index] = np.bincount(
                self.labels[clusters[selected_cluster_index]], minlength=self.labels.max() + 1).argmax()

        self.plot_accuracy_history()
        self.clusters = clusters

    def evaluate_accuracy(self, clusters: list):
        """
        Evaluates and tracks the accuracy of the current clusters.

        Args:
            clusters (list): List of clusters with sample indices.
        """
        total_samples_in_clusters = sum(len(cluster) for cluster in clusters)
        accuracies = [self.train_and_evaluate_nn(clusters) for _ in range(3)]
        self.accuracy_history.append((total_samples_in_clusters, accuracies))
        avg_accuracy = sum(accuracies) / len(accuracies)
        if avg_accuracy > self.max_avg_accuracy:
            self.max_avg_accuracy = avg_accuracy
            self.best_clusters = [list(cluster) for cluster in clusters]

    @staticmethod
    def _compute_metrics(y_true, y_pred):
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        total = tp + tn + fp + fn
        acc = (tp + tn) / total if total else 0.0
        sen = tp / (tp + fn) if (tp + fn) else 0.0  # Sensitivity/Recall/TPR
        spe = tn / (tn + fp) if (tn + fp) else 0.0  # Specificity/TNR
        return {"accuracy": acc * 100, "sensitivity": sen * 100, "specificity": spe * 100}

    def count_labels_in_clusters(self, clusters: list) -> dict:
        """
        Counts the number of samples with labels 0 and 1 in each cluster.

        Args:
            clusters (list of lists): List of clusters, each containing a list of sample indices.

        Returns:
            dict: A dictionary with counts of labels 0 and 1 in the clusters.
        """
        label_count = {'label_0': 0, 'label_1': 0}
        for cluster in clusters:
            for sample_index in cluster:
                label = self.labels[sample_index]
                if label == 0:
                    label_count['label_0'] += 1
                elif label == 1:
                    label_count['label_1'] += 1

        return label_count

    def train_and_evaluate_nn_2(self) -> float:
        """
        Trains and evaluates a neural network on the entire dataset.
        Returns:
            float: Accuracy (%) on the test dataset.
        """
        X_train, X_test, y_train, y_test = train_test_split(
            self.features, self.labels, test_size=0.2, random_state=42
        )
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = Sequential([
            Input(shape=(X_train_scaled.shape[1],)),
            Dense(64, activation='relu'),
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer=Adam(), loss='binary_crossentropy', metrics=['accuracy'])
        model.fit(X_train_scaled, y_train, epochs=15, batch_size=32, validation_split=0.2, verbose=0)

        y_prob = model.predict(X_test_scaled, verbose=0).ravel()
        y_pred = (y_prob >= 0.5).astype(int)

        m = self._compute_metrics(y_test, y_pred)
        print(f"Overall Neural Network — Acc: {m['accuracy']:.2f}%, "
            f"Sensitivity: {m['sensitivity']:.2f}%, Specificity: {m['specificity']:.2f}%")
        return m["accuracy"]
        
    def train_and_evaluate_rf_2(self) -> float:
        """
        Trains and evaluates a Random Forest classifier on the entire dataset (no clustering baseline).
        Returns:
            float: Accuracy (%) on the test dataset.
        """
        X_train, X_test, y_train, y_test = train_test_split(
            self.features, self.labels, test_size=0.2, random_state=42
        )
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)
        y_pred = rf_model.predict(X_test)

        m = self._compute_metrics(y_test, y_pred)
        print(f"Overall Random Forest — Acc: {m['accuracy']:.2f}%, "
            f"Sensitivity: {m['sensitivity']:.2f}%, Specificity: {m['specificity']:.2f}%")
        return m["accuracy"]

    def train_and_evaluate_xgb_2(self) -> float:
        """
        Trains and evaluates an XGBoost classifier on the entire dataset (no clustering baseline).
        Returns:
            float: Accuracy (%) on the test dataset.
        """
        X_train, X_test, y_train, y_test = train_test_split(
            self.features, self.labels, test_size=0.2, random_state=42
        )
        xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
        xgb_model.fit(X_train, y_train)
        y_pred = xgb_model.predict(X_test)

        m = self._compute_metrics(y_test, y_pred)
        print(f"Overall XGBoost — Acc: {m['accuracy']:.2f}%, "
            f"Sensitivity: {m['sensitivity']:.2f}%, Specificity: {m['specificity']:.2f}%")
        return m["accuracy"]

    def train_and_evaluate_nn(self, clusters: list, flag: int = 0) -> float:
        """
        Trains and evaluates a neural network on the clustered data.
        Returns:
            float: Accuracy (%) on the test dataset.
        """
        clustered_data_indices = [index for cluster in clusters for index in cluster]
        clustered_features = self.features[clustered_data_indices]
        clustered_labels = self.labels[clustered_data_indices]

        X_train, X_test, y_train, y_test = train_test_split(
            clustered_features, clustered_labels, test_size=0.2, random_state=42
        )
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = Sequential([
            Input(shape=(X_train_scaled.shape[1],)),
            Dense(64, activation='relu'),
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer=Adam(), loss='binary_crossentropy', metrics=['accuracy'])
        model.fit(X_train_scaled, y_train, epochs=15, batch_size=32, validation_split=0.2, verbose=0)

        y_prob = model.predict(X_test_scaled, verbose=0).ravel()
        y_pred = (y_prob >= 0.5).astype(int)

        m = self._compute_metrics(y_test, y_pred)
        print(f"Neural Network (clusters) — Acc: {m['accuracy']:.2f}%, "
            f"Sensitivity: {m['sensitivity']:.2f}%, Specificity: {m['specificity']:.2f}%")

        if flag == 1:
            try:
                model.save('app/services/models/ML_model_for_stroke_prediction.h5')
            except Exception as e:
                print(f"Error saving model: {e}")

        return m['accuracy']

    def train_and_evaluate_rf(self, clusters: list, flag: int = 0) -> float:
        """
        Trains and evaluates a Random Forest classifier on the clustered data.
        Returns:
            float: Accuracy (%) on the test dataset.
        """
        clustered_data_indices = [index for cluster in clusters for index in cluster]
        clustered_features = self.features[clustered_data_indices]
        clustered_labels = self.labels[clustered_data_indices]

        X_train, X_test, y_train, y_test = train_test_split(
            clustered_features, clustered_labels, test_size=0.2, random_state=42
        )
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)
        y_pred = rf_model.predict(X_test)

        m = self._compute_metrics(y_test, y_pred)
        print(f"Random Forest (clusters) — Acc: {m['accuracy']:.2f}%, "
            f"Sensitivity: {m['sensitivity']:.2f}%, Specificity: {m['specificity']:.2f}%")

        if flag == 1:
            try:
                joblib.dump(rf_model, 'app/services/models/RF_model_for_stroke_prediction.pkl')
            except Exception as e:
                print(f"Error saving Random Forest model: {e}")

        return m['accuracy']

    def train_and_evaluate_xgb(self, clusters: list, flag: int = 0) -> float:
        """
        Trains and evaluates an XGBoost classifier on the clustered data.
        Returns:
            float: Accuracy (%) on the test dataset.
        """
        clustered_data_indices = [index for cluster in clusters for index in cluster]
        clustered_features = self.features[clustered_data_indices]
        clustered_labels = self.labels[clustered_data_indices]

        X_train, X_test, y_train, y_test = train_test_split(
            clustered_features, clustered_labels, test_size=0.2, random_state=42
        )
        xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
        xgb_model.fit(X_train, y_train)
        y_pred = xgb_model.predict(X_test)

        m = self._compute_metrics(y_test, y_pred)
        print(f"XGBoost (clusters) — Acc: {m['accuracy']:.2f}%, "
            f"Sensitivity: {m['sensitivity']:.2f}%, Specificity: {m['specificity']:.2f}%")

        if flag == 1:
            try:
                xgb_model.save_model('app/services/models/XGB_model_for_stroke_prediction.json')
            except Exception as e:
                print(f"Error saving XGBoost model: {e}")

        return m['accuracy']
    
    def plot_accuracy_history(self):
        """
        Plots the accuracy history for each sample count during incremental clustering.
        """
        plt.figure(figsize=(12, 6))
        for sample_count, accuracies in self.accuracy_history:
            plt.scatter([sample_count] * len(accuracies), accuracies, alpha=0.6)

        plt.title('Accuracy Scatter Plot by Sample Count')
        plt.xlabel('Sample Count')
        plt.ylabel('Accuracy (%)')
        plt.grid(True)
        plt.show()


if __name__ == "__main__":
    file_path = 'app/services/data/data_clean.xlsx'
    divider = 2
    interval_divider = IntervalDivider(file_path, divider)

    grid_map = interval_divider.grid_map
    threshold = 0.3

    merger = GridMerger(grid_map, threshold)
    final_grid_map, histograms = merger.merge_until_threshold(interval_divider.data)

    len_threshold = 2
    len_threshold_0 = 2
    len_threshold_1 = 3
    num_threshold_0 = 0.7
    num_threshold_1 = 0.7

    processor = GridProcessor(final_grid_map, histograms, file_path, len_threshold, len_threshold_0, len_threshold_1, num_threshold_0, num_threshold_1)
    new_final_grid_map = processor.select_majority_grids()

    initial_clusters = []
    for grid_id, samples in new_final_grid_map.items():
        initial_clusters.append(samples)

    gkm = GravitationalKMeans(pd.read_excel(file_path), initial_clusters, enhancement_factor=0.0, eval_every=3, eval_stop_at=200)
    gkm.fit_incremental()

    print("*" * 100)
    nn_base = gkm.train_and_evaluate_nn_2()
    rf_base = gkm.train_and_evaluate_rf_2()
    xgb_base = gkm.train_and_evaluate_xgb_2()
    print("Baselines -> NN: %.2f%%, RF: %.2f%%, XGB: %.2f%%" % (nn_base, rf_base, xgb_base))

    print("*" * 100)
    print(gkm.max_avg_accuracy)
    print(gkm.best_clusters)

    accuracy = gkm.train_and_evaluate_nn(gkm.best_clusters, flag=1)
    print(accuracy)

    print("*" * 100)
    accuracy = gkm.train_and_evaluate_rf(gkm.best_clusters, flag=1)
    print(accuracy)

    print("*" * 100)
    accuracy = gkm.train_and_evaluate_xgb(gkm.best_clusters, flag=1)
    print(accuracy)