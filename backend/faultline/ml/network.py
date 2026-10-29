"""A small tanh MLP with explicitly derived gradients and Adam."""
from collections.abc import Callable
import numpy as np


class MLP:
    def __init__(self, input_size: int, hidden_size: int = 32, seed: int = 7):
        self.seed = seed
        rng = np.random.default_rng(seed)
        self.params = {
            "w1": rng.normal(0, np.sqrt(2 / (input_size + hidden_size)), (input_size, hidden_size)),
            "b1": np.zeros(hidden_size),
            "w2": rng.normal(0, np.sqrt(2 / (hidden_size + 3)), (hidden_size, 3)),
            "b2": np.zeros(3),
        }

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(x @ self.params["w1"] + self.params["b1"]) @ self.params["w2"] + self.params["b2"]

    def loss_and_gradients(self, x: np.ndarray, y: np.ndarray) -> tuple[float, dict]:
        p = self.params
        hidden = np.tanh(x @ p["w1"] + p["b1"])
        error = hidden @ p["w2"] + p["b2"] - y
        output_grad = 2 * error / error.size
        hidden_grad = (output_grad @ p["w2"].T) * (1 - hidden**2)
        return float(np.mean(error**2)), {
            "w1": x.T @ hidden_grad, "b1": hidden_grad.sum(axis=0),
            "w2": hidden.T @ output_grad, "b2": output_grad.sum(axis=0),
        }

    def fit(self, x: np.ndarray, y: np.ndarray, epochs: int = 60, batch_size: int = 512,
            progress: Callable | None = None, validation: tuple | None = None) -> list[dict]:
        rng = np.random.default_rng(self.seed)
        m = {k: np.zeros_like(v) for k, v in self.params.items()}
        v = {k: np.zeros_like(p) for k, p in self.params.items()}
        step, curve = 0, []
        for epoch in range(epochs):
            order = rng.permutation(len(x))
            for offset in range(0, len(x), batch_size):
                batch = order[offset:offset + batch_size]
                _, gradients = self.loss_and_gradients(x[batch], y[batch])
                step += 1
                for key, gradient in gradients.items():
                    m[key] = .9 * m[key] + .1 * gradient
                    v[key] = .999 * v[key] + .001 * gradient**2
                    self.params[key] -= .003 * (m[key] / (1 - .9**step)) / (np.sqrt(v[key] / (1 - .999**step)) + 1e-8)
            point = {"epoch": epoch + 1, "loss": float(np.mean((self.predict(x) - y)**2))}
            if validation:
                point["validation_loss"] = float(np.mean((self.predict(validation[0]) - validation[1])**2))
            curve.append(point)
            if progress:
                progress(epoch + 1, epochs)
        return curve
