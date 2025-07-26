from flask import Flask, request, jsonify
from requests import post
from threading import Thread
from random import random
from transformers import pipeline
from scipy.stats import ttest_ind
from tabulate import tabulate
import pandas as pd
import time

"""
This implementation simulates A/B testing by running two servers on localhost 
which correspond to two different text-generation models.

The client requests are randomly assigned to any of the servers and the response 
from the server gets some feedback either randomly or by input.

The feedbacks are used for t-test to find out if there is statistically 
significant difference to say that model B is better than model A.
"""


class ModelServer:
    def __init__(self, name, deployment):
        self.name = name
        self.host, self.port = deployment.split(':')
        assert self.host == 'localhost'
        self.generator = pipeline('text-generation', model=name, framework='pt')

    def run(self):
        app = Flask(self.name)

        @app.route('/generate', methods=['POST'])
        def generate():
            data = request.json
            prompt = data['prompt']
            response = self.generator(prompt, max_new_tokens=10)
            return jsonify({"prompt": prompt, "model": self.name, "response": response})

        app.run(port=self.port)

    def run_as_daemon_thread(self):
        daemon_thread = Thread(target=self.run, daemon=True)
        daemon_thread.start()


class Client:
    def __init__(self, servers, feedback_mode):
        self.servers = servers

        if feedback_mode not in ["input", "random"]:
            raise ValueError("Invalid feedback mode")

        self.feedback_mode = feedback_mode
        self.outputs = []

    def test_model_servers(self, prompt):
        response = self.send_request(prompt)
        output = response.json()
        print("Prompt: ", prompt)
        print("Response: ", output['response'])

        if self.feedback_mode == "random":
            feedback = round(random())
            print(f"Feedback: {feedback}\n")
        else:
            feedback = int(input("Enter 1 for positive and 0 for negative feedback: "))

        output['feedback'] = feedback
        self.outputs.append(output)

    def send_request(self, prompt):
        server = self.servers[0] if random() < 0.5 else self.servers[1]
        return post(f"http://{server.host}:{server.port}/generate", json={"prompt": prompt})


class ABTester:
    def __init__(self, models, p_value_threshold, verbose=True):
        self.models = models
        self.p_value_threshold = p_value_threshold
        self.verbose = verbose

    def test(self, feedbacks):
        df = pd.DataFrame(feedbacks)
        if self.verbose:
            self.show(df, format='grid')

        a = df[df['model'] == self.models[0]]['feedback']
        b = df[df['model'] == self.models[1]]['feedback']
        t_stat, p_value = ttest_ind(b, a)
        print(f"t-stat: {t_stat}, p-value: {p_value}\n")

        if self.verbose:
            self.analyze(t_stat, p_value)

    def show(self, df, format):
        print(tabulate(df, headers='keys', showindex=False, tablefmt=format))

    def analyze(self, t_stat, p_value):
        if t_stat > 0:
            p_value_one_tailed = p_value / 2
        else:
            p_value_one_tailed = 1 - (p_value / 2)

        print(f"One-tailed p-value: {p_value_one_tailed}, threshold: {self.p_value_threshold}")
        if p_value_one_tailed < self.p_value_threshold:
            print(f"Statistically significant difference to say that {self.models[1]} is better!")
        else:
            print(f"Not enough evidence to say that {self.models[1]} is better than {self.models[0]}.")


if __name__ == '__main__':
    models = ['gpt2', 'gpt2-medium']
    deployments = ['localhost:5001', 'localhost:5002']

    server_a = ModelServer(name=models[0], deployment=deployments[0])
    server_b = ModelServer(name=models[1], deployment=deployments[1])

    server_a.run_as_daemon_thread()
    server_b.run_as_daemon_thread()

    print("Waiting for servers to be healthy..")
    time.sleep(10)

    client = Client(servers=[server_a, server_b], feedback_mode="random")
    client.test_model_servers(prompt="About India")
    client.test_model_servers(prompt="About France")
    client.test_model_servers(prompt="About USA")
    client.test_model_servers(prompt="About China")

    ab_tester = ABTester(models=models, p_value_threshold=0.05)
    ab_tester.test(client.outputs)
