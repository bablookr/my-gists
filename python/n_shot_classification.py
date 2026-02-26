from abc import ABC, abstractmethod
from PIL import Image
from transformers import TFCLIPModel, CLIPProcessor
from huggingface_hub import snapshot_download
import numpy as np
import tensorflow as tf
import tf_keras as keras

"""
This class is a basic demonstration of zero-shot, one-shot and 
few-shot classification on CIFAR-10 and MNIST images.

We use pretrained models from HuggingFace for this purpose:
- Zero-shot model: openai/clip-vit-base-patch32
- One/Few-shot model: keras-io/siamese-contrastive
"""


class NShotClassifier(ABC):
    @abstractmethod
    def add_label(self, examples, label):
        pass

    @abstractmethod
    def predict(self, image):
        pass

    @abstractmethod
    def test(self, dataset):
        pass


class ZeroShotClassifier(NShotClassifier):
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.model = TFCLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.labels = []

    def add_label(self, label, examples=None):
        self.labels.append(label)

    def predict(self, image_array):
        image = Image.fromarray(image_array).convert("RGB")
        inputs = self.processor(
            text=self.labels,
            images=image,
            return_tensors="tf",
            padding=True
        )
        outputs = self.model(**inputs)
        probs = tf.nn.softmax(outputs.logits_per_image, axis=1)
        idx = tf.argmax(probs[0]).numpy()
        return self.labels[idx], float(probs[0][idx])

    def test(self, dataset):
        print("Testing zero-shot classification on CIFAR-10...")
        (_, _), (x_test, y_test) = dataset
        test_img = x_test[0]
        test_label = y_test[0][0]

        cifar_labels = ["airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck"]
        true_label = cifar_labels[test_label]

        candidate_labels = ["cat", "dog", "truck"]
        for label in candidate_labels:
            self.add_label(label)

        prediction, score = self.predict(test_img)
        print("True label      :", true_label)
        print("Candidate set   :", candidate_labels)
        print("Predicted label :", prediction)
        print("Confidence      :", score)
        print()


class FewShotClassifier(NShotClassifier):
    def __init__(self, n, model_name="keras-io/siamese-contrastive"):
        self.n = n
        model = keras.models.load_model(snapshot_download(model_name), compile=False)
        self.encoder = [layer for layer in model.layers if layer.name == "model"][0]
        self.images = {}

    def embed(self, image_array):
        img = image_array.astype("float32") / 255.0
        img = np.expand_dims(img, (0, -1))  # (1,28,28,1)
        emb = self.encoder(img)
        return tf.squeeze(emb)

    def add_label(self, examples, label):
        embeddings = [self.embed(x) for x in examples]
        prototype = tf.reduce_mean(embeddings, axis=0)
        self.images[label] = prototype

    def predict(self, image_array, threshold=1.0):
        query_emb = self.embed(image_array)
        best_label = None
        min_dist = float("inf")
        for label, prototype in self.images.items():
            dist = tf.norm(query_emb - prototype).numpy()
            if dist < min_dist:
                min_dist = dist
                best_label = label
        if min_dist <= threshold:
            return best_label, min_dist
        else:
            return "Unknown", min_dist

    def test(self, dataset):
        print(f"Testing {self.n}-shot classification on MNIST...")
        (x_train, y_train), (_, _) = dataset
        ones = x_train[np.where(y_train == 1)[0]]

        imgs_of_11 = [create_new_sample(ones[i], ones[i + 1]) for i in range(0, 2 * self.n, 2)]
        true_label = "11"
        self.add_label(imgs_of_11, true_label)

        new_img_of_11 = create_new_sample(ones[2], ones[3])
        prediction, dist = self.predict(new_img_of_11)

        print("True label      :", true_label)
        print("Predicted label :", prediction)
        print("Min distance    :", dist)
        print()


def create_new_sample(img1, img2, size=(28, 28)):
    img = np.concatenate([img1, img2], axis=1)
    img = tf.image.resize(img[..., None], size)
    return tf.squeeze(img).numpy()


if __name__ == "__main__":
    cifar10 = keras.datasets.cifar10.load_data()
    zero_shot_clf = ZeroShotClassifier()
    zero_shot_clf.test(cifar10)

    mnist = keras.datasets.mnist.load_data()
    one_shot_clf = FewShotClassifier(n=1)
    one_shot_clf.test(mnist)

    few_shot_clf = FewShotClassifier(n=4)
    few_shot_clf.test(mnist)
