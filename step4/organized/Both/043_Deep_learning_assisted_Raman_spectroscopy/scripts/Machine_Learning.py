from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
import pandas as pd
import numpy as np
from sklearn.model_selection import cross_validate
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import cross_val_score,cross_val_predict,  KFold,  LeaveOneOut, StratifiedKFold
from sklearn.metrics import confusion_matrix
import os
from sklearn.decomposition import PCA, IncrementalPCA
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
# model lg/svm/lda
model = 'lg pca'

# standard label
One_folder = '0'
Two_folder = '1'
directory_name = './MachineLearning/B/'


features_class = []
label_class = []
for file in os.listdir(directory_name + One_folder):
    csv_class = pd.read_csv(directory_name + One_folder + '/' + file).to_numpy()
    features_class.extend(csv_class[0:, :])
    label_class.extend(np.full(shape=len(csv_class), fill_value=1, dtype=np.int))

for file in os.listdir(directory_name + Two_folder):
    csv_class = pd.read_csv(directory_name + Two_folder + '/' + file).to_numpy()
    features_class.extend(csv_class[0:, :])
    label_class.extend(np.full(shape=len(csv_class), fill_value=2, dtype=np.int))

features_class = np.array(features_class)
# ss = StandardScaler()
# ss.fit(features_class)
# features_class = ss.transform(features_class)

pc_n = 10
if 'pca' in model:
    pca = PCA(n_components=pc_n)
    scaler = StandardScaler()
    scaler.fit(features_class)
    features_class = scaler.transform(features_class)
    pca.fit(features_class)
    X_pca = pca.fit_transform(features_class)
    features_class = X_pca
    X=features_class
    y=label_class
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True)

# LDA SVM LG classifier
if 'lda' in model:
    clf = LDA()
    clf.fit(X_train, np.array(y_train))
    a=clf.coef_

# SVM
if 'svm' in model:
    from sklearn.svm import SVC
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    clf = make_pipeline(StandardScaler(), SVC(gamma='auto', probability=True, kernel='linear'))  #rbf
    clf.fit(X_train, np.array(y_train))


# LG
if 'lg' in model:
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(random_state=8, C=100, solver='liblinear') #sag


y_predicted=clf.transform(X_test)

fpr, tpr, threshold = roc_curve(y_test, y_predicted, pos_label=2)  # 计算真正率和假正率
roc_auc = auc(fpr, tpr)  # 计算auc的值
plt.figure()
plt.figure(figsize=(4, 4))
print('threshold', threshold)
print('1-Specificity', fpr)
print('Sensitivity', tpr)
plt.plot(fpr, tpr, color='darkorange', lw=3)
plt.plot([0, 1], [0, 1], color='navy', linestyle='--')
plt.xlim([-0.01, 1.01])
plt.ylim([-0.01, 1.01])
plt.xlabel('1-Specificity')
plt.ylabel('Sensitivity')
plt.title('ROC Curve (AUC = {})'.format(round(roc_auc, 3)))
plt.show()

# binary
all_probs = y_predicted
all_probs = [2 if x>=0.5 else x for x in all_probs]
all_probs = [1 if x<0.5 else x for x in all_probs]
all_y = y_test
tn, fp, fn, tp = confusion_matrix(all_y, all_probs).ravel()
Sen1 = tp / (tp + fn)
Spe1 = tn / (fp + tn)
Acc1 = (tp+tn) / (tn+fp+fn+tp)
print('confusion matrix tn fp fn tp', (tn, fp, fn, tp))
print('Sen Spe Acc',(Sen1,Spe1,Acc1))

joblib.dump(clf,'./test.pkl')

print('done')