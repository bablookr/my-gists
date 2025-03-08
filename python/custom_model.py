import random

import tensorflow as tf
from tensorflow.keras.callbacks import Callback
from tensorflow.keras.layers import Input, Layer
from tensorflow.keras.losses import Loss
from tensorflow.keras.metrics import BinaryAccuracy
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import SGD

"""
This is a tensorflow model with customized training and evaluation.

It also contains a custom layer, a custom loss function and a custom callback,
which are basically the simple forms of already existing implementations.

The main method fits and evaluates the model on randomly created datasets.
In order to make the simulation deterministic, we have set a seed value.

"""


class CustomModel(Model):
    def train_step(self, data):
        x, y = data

        with tf.GradientTape() as tape:
            y_pred = self(x, training=True)
            loss = self.compute_loss(y=y, y_pred=y_pred)

        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)
        self.optimizer.apply(gradients, trainable_vars)

        for metric in self.metrics:
            if metric.name == "loss":
                metric.update_state(loss)
            else:
                metric.update_state(y, y_pred)
        return {m.name: m.result() for m in self.metrics}

    def test_step(self, data):
        print("\nEvalaution starts...")
        x, y = data
        y_pred = self(x, training=False)

        loss = self.compute_loss(y=y, y_pred=y_pred)

        for metric in self.metrics:
            if metric.name == "loss":
                metric.update_state(loss)
            else:
                metric.update_state(y, y_pred)
        return {m.name: m.result() for m in self.metrics}


class SimpleLayer(Layer):
    def __init__(self, units):
        super().__init__()
        self.units = units

    def build(self, input_shape):
        self.w = self.add_weight(shape=(input_shape[-1], self.units), initializer="glorot_uniform", trainable=True)
        self.b = self.add_weight(shape=(self.units,), initializer="zeros", trainable=True)

    def call(self, inputs):
        return tf.sigmoid(tf.matmul(inputs, self.w) + self.b)


class SimpleLoss(Loss):
    def __init__(self, epsilon=1e-7):
        super().__init__()
        self.epsilon = epsilon

    def call(self, y_true, y_pred):
        y_pred = tf.clip_by_value(y_pred, self.epsilon, 1 - self.epsilon)
        bce = - y_true * tf.math.log(y_pred + self.epsilon) - (1 - y_true) * tf.math.log(1 - y_pred + self.epsilon)
        return tf.reduce_mean(bce)


class SimpleCallback(Callback):
    def on_batch_end(self, batch, logs=None):
        print("\nEnd of batch = ", batch, ", loss = ", logs['loss'])


if __name__ == '__main__':
    tf.random.set_seed(43)
    random.seed(43)

    # Create the training dataset
    x = tf.random.normal([1000, 32])
    y = tf.random.normal([1000, 1])
    y = tf.round(y)

    ds = tf.data.Dataset.from_tensor_slices((x, y))
    ds = ds.batch(256)

    # Create the custom model
    inputs = Input(shape=(32,))
    outputs = SimpleLayer(1)(inputs)
    model = CustomModel(inputs=inputs, outputs=outputs)
    model.compile(loss=SimpleLoss(), optimizer=SGD(), metrics=[BinaryAccuracy()])

    # Train the model
    run_with_callback = False
    if run_with_callback:
        model.fit(ds, epochs=3, callbacks=[SimpleCallback()])
    else:
        model.fit(ds, epochs=3)

    # Create the test dataset
    x_test = tf.random.uniform([10000, 32])
    y_test = tf.random.uniform([10000, 1])
    y_test = tf.round(y_test)
    test_ds = tf.data.Dataset.from_tensor_slices((x, y)).batch(512)

    # Test the model
    model.evaluate(test_ds)
