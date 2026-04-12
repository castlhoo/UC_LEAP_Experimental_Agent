import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
import pandas as pd
from scipy.signal import savgol_filter


# baseline_remove
def baseline_als(y, lam=100000, p=0.01, niter=10):
    L = len(y)
    D = sparse.csc_matrix(np.diff(np.eye(L), 2))
    w = np.ones(L)
    for i in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
        y = y - z  # subtract the background 'z' from the original data 'y'
    return y


# S-G filter
def sg_filter(x, window_length=11, polyorder=3):
    x = savgol_filter(x, window_length, polyorder)
    return x


# spectral normalization
def norm_func(x, a=0, b=1):
    return ((b - a) * (x - min(x))) / (max(x) - min(x)) + a


# combined preprocessing function
def preprocess(x, y=None):
    x = baseline_als(x, lam=100000, p=0.01, niter=10)
    x = sg_filter(x, window_length=11, polyorder=3)
    x = norm_func(x, a=0, b=1)
    return x


file = './combined-.csv'
df = pd.read_csv(file)

# data = preprocess(pd.read_csv(file).values)

m = df.shape[0]  # number of lines
n = df.shape[1]  # number of columns
print('number of lines:', m)
print('number of columns:', n)


matrix = np.ndarray(shape=(m, n))

for i in range(1, m + 1, 1):
    data = df.iloc[i - 1]
    data_p = preprocess(data)
    matrix[i - 1, :] = data_p
    print('line', i - 1, 'completed')

np.savetxt('combined-p.csv', matrix, delimiter=',') # save the matrix into a new csv file

print('well done')
