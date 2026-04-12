# Data manipulation
import pandas as pd # for data manipulation
import numpy as np # for data manipulation
from sklearn.metrics import roc_curve, auc
from sklearn.metrics import confusion_matrix
# Visualization
import plotly.express as px # for data visualization
import matplotlib.pyplot as plt # for showing handwritten digits
import seaborn as sns
# Skleran
from sklearn.model_selection import train_test_split # for splitting data into train and test samples

# UMAP dimensionality reduction
from umap import UMAP
import time

# 
csvfile = "./710422.csv"
csv_data = pd.read_csv(csvfile,low_memory=False)
#print(np.isnan(csv_data).any())
csv_data.dropna(inplace=True)
X = csv_data.values[0: , 1:]
y = csv_data.values[0: , 0]

from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
clf = make_pipeline(StandardScaler(), SVC(gamma='auto', probability=True, kernel='rbf'))  #rbf


# Configure UMAP hyperparameters
reducer = UMAP(n_neighbors=200, # default 15, The size of local neighborhood (in terms of number of neighboring sample points) used for manifold approximation.
               n_components=3, # default 2, The dimension of the space to embed into.
               metric='euclidean', # default 'euclidean', The metric to use to compute distances in high dimensional space.
               n_epochs=1000, # default None, The number of training epochs to be used in optimizing the low dimensional embedding. Larger values result in more accurate embeddings.
               learning_rate=1.0, # default 1.0, The initial learning rate for the embedding optimization.
               init='spectral', # default 'spectral', How to initialize the low dimensional embedding. Options are: {'spectral', 'random', A numpy array of initial embedding positions}.
               min_dist=0.1, # default 0.1, The effective minimum distance between embedded points.
               spread=1.0, # default 1.0, The effective scale of embedded points. In combination with ``min_dist`` this determines how clustered/clumped the embedded points are.
               low_memory=False, # default False, For some datasets the nearest neighbor computation can consume a lot of memory. If you find that UMAP is failing due to memory constraints consider setting this option to True.
               set_op_mix_ratio=1.0, # default 1.0, The value of this parameter should be between 0.0 and 1.0; a value of 1.0 will use a pure fuzzy union, while 0.0 will use a pure fuzzy intersection.
               local_connectivity=1, # default 1, The local connectivity required -- i.e. the number of nearest neighbors that should be assumed to be connected at a local level.
               repulsion_strength=1.0, # default 1.0, Weighting applied to negative samples in low dimensional embedding optimization.
               negative_sample_rate=5, # default 5, Increasing this value will result in greater repulsive force being applied, greater optimization cost, but slightly more accuracy.
               transform_queue_size=4.0, # default 4.0, Larger values will result in slower performance but more accurate nearest neighbor evaluation.
               a=None, # default None, More specific parameters controlling the embedding. If None these values are set automatically as determined by ``min_dist`` and ``spread``.
               b=None, # default None, More specific parameters controlling the embedding. If None these values are set automatically as determined by ``min_dist`` and ``spread``.
               random_state=42, # default: None, If int, random_state is the seed used by the random number generator;
               metric_kwds=None, # default None) Arguments to pass on to the metric, such as the ``p`` value for Minkowski distance.
               angular_rp_forest=False, # default False, Whether to use an angular random projection forest to initialise the approximate nearest neighbor search.
               target_n_neighbors=-1, # default -1, The number of nearest neighbors to use to construct the target simplcial set. If set to -1 use the ``n_neighbors`` value.
               #target_metric='categorical', # default 'categorical', The metric used to measure distance for a target array is using supervised dimension reduction. By default this is 'categorical' which will measure distance in terms of whether categories match or are different.
               #target_metric_kwds=None, # dict, default None, Keyword argument to pass to the target metric when performing supervised dimension reduction. If None then no arguments are passed on.
               #target_weight=0.5, # default 0.5, weighting factor between data topology and target topology.
               transform_seed=42, # default 42, Random seed used for the stochastic aspects of the transform operation.
               verbose=False, # default False, Controls verbosity of logging.
               unique=False, # default False, Controls if the rows of your data should be uniqued before being embedded.
              )


# # Fit and transform the data
# X_trans = reducer.fit_transform(X)
#
# # Check the shape of the new data
# print('Shape of X_trans: ', X_trans.shape)

# Split data into training and testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True)

# Configure UMAP hyperparameters
reducer2 = UMAP(n_neighbors=200, n_components=3, n_epochs=1000,
                min_dist=0.5, local_connectivity=2, random_state=42,
              )

# Training on MNIST digits data - this time we also pass the true labels to a fit_transform method
# tic = time.time()
X_train_res = reducer2.fit_transform(X_train, y_train)
tic = time.time()
# Apply on a test set
X_test_res = reducer2.transform(X_test)


clf.fit(X_train_res, np.array(y_train))
y_predicted=clf.predict_proba(X_test_res)[:,1] #SVM

toc = time.time()
shijian = toc-tic
# print('Time:',round(shijian, 4),'s')

fpr, tpr, threshold = roc_curve(y_test, y_predicted, pos_label=1)  # 计算真正率和假正率
A_sub = []
A_sub.append(fpr)
A_sub.append(tpr)
A_sub.append(threshold)
A_result = pd.DataFrame(A_sub)
A_result.to_excel(csvfile +'_roc UMAP' + '.xlsx')

roc_auc = auc(fpr, tpr)  #
plt.figure()
plt.figure(figsize=(4, 4))
# print('threshold', threshold)
# print('1-Specificity', fpr)
# print('Sensitivity', tpr)
plt.plot(fpr, tpr, color='darkorange', lw=3)
plt.plot([0, 1], [0, 1], color='navy', linestyle='--')

# cutoff
c1=(1-tpr)*(1-tpr)+fpr*fpr
c1=c1.tolist()
ind=c1.index(min(c1))
th = threshold[ind]
fpr=fpr.tolist()
tpr=tpr.tolist()
plt.scatter(fpr[ind], tpr[ind], s=300,marker="P",color='darkorange')

plt.xlim([-0.01, 1.01])
plt.ylim([-0.01, 1.01])
plt.xlabel('1-Specificity')
plt.ylabel('Sensitivity')
plt.title('ROC Curve (AUC = {})'.format(round(roc_auc, 3)),fontsize=20)
plt.savefig(csvfile + '_roc curve UMAP' + '.png')
plt.show()

# binary
all_probs = y_predicted
all_probs = [1 if x>=th else x for x in all_probs]
all_probs = [0 if x<th else x for x in all_probs]
all_y = y_test

tn, fp, fn, tp = confusion_matrix(all_y, all_probs).ravel()
cm = confusion_matrix(all_y, all_probs, labels=None, sample_weight=None)

def plot_confusion_matrix(cm, classes, title='Confusion matrix', cmap=plt.cm.jet):
    sns.set()
    fig, ax = plt.subplots()
    sns.heatmap(cm, annot=True, fmt='g', ax=ax, cmap="YlGnBu",annot_kws={"fontsize":50})  # Colors: YlGnBu
    # ax.set_xlabel('Predicted Label')
    # ax.set_ylabel('Actual Label')
    # plt.savefig('./confusion_matrix_ID.png')
    # plt.savefig(csvfile + 'confusion_matrix_ID UMAP' + '.png')
    # plt.show()

classs = ['0', '1']
plot_confusion_matrix(cm, 'confusion_matrix.png', classs)
Sen1 = tp / (tp + fn)
Spe1 = tn / (fp + tn)
Acc1 = (tp+tn) / (tn+fp+fn+tp)


B_sub = (Sen1,Spe1,Acc1,shijian)
B_result = pd.DataFrame(B_sub)
B_result.to_excel(csvfile + '_metrics UMAP' + '.xlsx')


plt.figure()
plt.axis('off')
plt.text(0, 0.8, 'Sensitivity : '+str(round(Sen1, 4)),fontsize=36,family='DejaVu Sans')
plt.text(0, 0.6, 'Specificity : '+str(round(Spe1, 4)),fontsize=36,family='DejaVu Sans')
plt.text(0, 0.4, 'Accuracy : '+str(round(Acc1, 4)),fontsize=36,family='DejaVu Sans')
plt.text(0, 0.2, 'Time : '+str(round(shijian, 4))+' s',fontsize=36,family='DejaVu Sans')
plt.savefig(csvfile + '_metrics UMAP' + '.png')
plt.show()



fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.set_facecolor('white')
ax.w_xaxis.line.set_color('gray')
ax.w_yaxis.line.set_color('gray')
ax.w_zaxis.line.set_color('gray')
# ax.tick_params(axis='y',colors='red')#
ax.w_xaxis.set_pane_color((0.9, 0.9, 0.95, 1.0))
ax.w_yaxis.set_pane_color((0.9, 0.9, 0.95, 1.0))
ax.w_zaxis.set_pane_color((0.9, 0.9, 0.95, 1.0))
#
X_train_res0=X_train_res[np.where(y_train == 0)]
X_train_res1=X_train_res[np.where(y_train == 1)]
X_test_res0=X_test_res[np.where(y_test == 0)]
X_test_res1=X_test_res[np.where(y_test == 1)]
ax.scatter( X_train_res0[:,0], X_train_res0[:,1], X_train_res0[:,2],c='navajowhite', marker='^',label='IDH Wild',fontsize=30)# 绘图
ax.scatter( X_train_res1[:,0], X_train_res1[:,1], X_train_res1[:,2],c='lightgreen', marker='^',label='IDH Mutation',fontsize=30)
ax.scatter( X_test_res0[:,0], X_test_res0[:,1], X_test_res0[:,2],c='orange', marker='^',label='test-0',fontsize=30)
ax.scatter( X_test_res1[:,0], X_test_res1[:,1], X_test_res1[:,2],c='forestgreen', marker='^',label='test-1',fontsize=30)
plt.legend(fontsize=30,loc='upper right')
#
ax.set_xlabel('UMAP 1',fontsize=30,labelpad = 20)
ax.set_ylabel('UMAP 2',fontsize=30,labelpad = 20)
ax.set_zlabel('UMAP 3',fontsize=30,labelpad = 20)
plt.tick_params(labelsize=23)
plt.savefig(csvfile + '_projection UMAP' + '.png')
plt.show()




