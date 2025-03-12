# Principal Component Analysis

Let $\mathbf{X}$ be an $n \times p$ matrix representing a dataset with $n$ samples and $p$ features.

$$\begin{equation}
    \begin{aligned}
        & \text{Covariance matrix of } X,
        & C 
        & = 
        & \frac{1}{n}\\ X^TX
    \end{aligned}
\end{equation}$$

If $w$ is a $p$-dimension unit vector, 

$$\begin{equation}
    \begin{aligned}
        & \text{Projection of } X \text{ along } w,
        & P 
        & = 
        & Xw \\
        & \text{Variance of } P,
        & \sigma^2 
        & = 
        & \frac{1}{n}\\ P^TP \\
        &&& =
        & \frac{1}{n}\\ (Xw)^TXw \\
        &&& =
        & \frac{1}{n}\\ w^TX^TXw \\
        &&& =
        & w^TCw
    \end{aligned}
\end{equation}$$

Let's summarize the above equations as a table:

<center>

|           |  $X$         | $C$          | $w$          | $P$          | $\sigma^2$   |
| --------- | ------------ | ------------ | ------------ | ------------ | ------------ |
| **Shape** | $n \times p$ | $p \times p$ | $p \times 1$ | $n \times 1$ | $1 \times 1$ |
  
</center>

## Optimization Problem

If we want to find the unit vector which maximizes this variance, the constrained optimization problem is:

$$\begin{equation}
    \begin{aligned}
        & Maximize & w^TCw & s.t. & w^Tw = 1
    \end{aligned}
\end{equation}$$

### Solution

Using the method of Lagrange multipliers, 

$$\mathcal{L}(w, \lambda) = w^TCw - \lambda(w^Tw-1)$$

Differenting w.r.t. $w$ and $\lambda$, we get -

$$2Cw - 2\lambda w = 0$$ 

$$w^Tw - 1 = 0$$ 

Simplifying -

$$Cw = \lambda w$$ 

$$w^Tw = 1$$ 

#### Getting the value of w and $\lambda$

If $Cw = \lambda w$, $w$ is an eigenvector of $C$ and $\lambda$ is an eigenvalue of $C$.

Find the values of $\lambda$ by solving the following equation:

$$det(C-\lambda I) = 0$$

Find the values of $w$ by substituting $\lambda$ and solving the equation:

$$(C-\lambda I)w = 0$$

Note that as the maximum number of eigenvalues for a $p \times p$ matrix = $p$, the maximum number of possible values of $\lambda$ for the above equation is also $p$.

### Dimensionality Reduction

For each unit vector $w$,

$$\begin{equation}
    \begin{aligned}
        & \text{Projection of } X \text{ along } w,
        & P 
        & = 
        & Xw \\
        & \text{Variance of } P,
        & \sigma^2 
        & = 
        & w^TCw \\
        &&& =
        & w^T\lambda w \\
        &&& = 
        & \lambda w^Tw \\
        &&& = 
        & \lambda
    \end{aligned}
\end{equation}$$

We select $k$ unit vectors with the highest variance of projection of $X$ (where $k \leq p$) and find the projections of $X$ along them.

And thus $X$ is reduced from an $n \times p$ matrix to an $n \times k$ matrix (as shape of each projection is $n \times 1$).

## Implementation

### Scratch implementation using numpy
```python
import numpy as np

def pca(X, k):
    X_meaned = X - np.mean(X , axis=0)
    X_std = X_meaned / np.std(X_meaned , axis=0)
    covariance_matrix = np.cov(X_std , rowvar=False)
    
    eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
    sorted_idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[sorted_idx]
    eigenvectors = eigenvectors[:, sorted_idx]
    
    eigenvectors_subset = eigenvectors[:, :k]
    X_reduced = np.dot(X_std, eigenvectors_subset)
    
    return X_reduced, eigenvalues
```

### Inbuilt implementation using sklearn
```python
from sklearn.decomposition import PCA

def pca(X, k):
    pca = PCA(n_components=k)
    pca.fit(X)

    transformed_data = pca.transform(X)
    explained_variance = pca.explained_variance_

    return transformed_data, explained_variance
```
