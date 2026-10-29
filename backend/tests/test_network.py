import numpy as np
from faultline.ml.network import MLP


def test_analytic_backprop_matches_finite_differences():
    net = MLP(3, hidden_size=4, seed=3)
    x = np.array([[.2, -.1, .8], [.3, .6, -.5]])
    y = np.array([[.1, .3, -.4], [.5, -.2, .7]])
    _, gradients = net.loss_and_gradients(x, y)
    for name, param in net.params.items():
        for index in np.ndindex(param.shape):
            original = param[index]
            param[index] = original + 1e-5
            plus = net.loss_and_gradients(x, y)[0]
            param[index] = original - 1e-5
            minus = net.loss_and_gradients(x, y)[0]
            param[index] = original
            assert abs(gradients[name][index] - (plus - minus) / 2e-5) < 1e-7


def test_adam_learns_multivariate_relationship_reproducibly():
    rng = np.random.default_rng(8)
    x = rng.normal(size=(150, 3))
    y = x * .5 + .2
    a, b = MLP(3, seed=9), MLP(3, seed=9)
    before = np.mean((a.predict(x) - y)**2)
    curve = a.fit(x, y, epochs=80, batch_size=64)
    b.fit(x, y, epochs=80, batch_size=64)
    assert curve[-1]["loss"] < before * .06
    np.testing.assert_array_equal(a.predict(x), b.predict(x))
