import numpy as np
import pandas as pd
#import google.protobuf
import seaborn as sns
import keras
from keras.models import Sequential
from keras.wrappers.scikit_learn import KerasClassifier
from keras.wrappers.scikit_learn import KerasRegressor
from sklearn.utils import class_weight
from keras.utils import np_utils

from keras.utils.vis_utils import plot_model
from sklearn.model_selection import cross_val_score, train_test_split, KFold
from sklearn.preprocessing import LabelEncoder
from keras.layers import Dense, Dropout, Flatten, Conv1D, MaxPooling1D,BatchNormalization,add,ZeroPadding1D,Input,AveragePooling1D
from keras.models import model_from_json,Model
from keras import regularizers
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
from sklearn.metrics import roc_curve, auc
import time
from keras.callbacks import History
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import GridSearchCV


# Load data
csvfile = "./710422.csv" #h
csv_data = pd.read_csv(csvfile,low_memory=False)
#print(np.isnan(csv_data).any())
csv_data.dropna(inplace=True)

X = np.expand_dims(csv_data.values[0: , 1:].astype(float), axis=2)
Y = csv_data.values[0: , 0]

#Encode
encoder = LabelEncoder()
Y_encoded = encoder.fit_transform(Y)
Y_onehot = np_utils.to_categorical(Y_encoded)

X_train, X_test, Y_train, Y_test = train_test_split(X, Y_onehot, test_size=0.1, random_state=0)

# resnet_34
def resnet_34():
    input1 = keras.layers.Input(shape=(807, 1)) #h
    x = ZeroPadding1D(1)(input1)
    x = Conv1d_BN(x, nb_filter=8, kernel_size=5, strides=1, padding='valid')
    x = Dropout(0.5)(x)

    x = identity_Block(x, nb_filter=8, kernel_size=5, strides=2, with_conv_shortcut=True) #h
    x = identity_Block(x, nb_filter=8, kernel_size=5, strides=1, with_conv_shortcut=False)

    x = identity_Block(x, nb_filter=16, kernel_size=5, strides=2, with_conv_shortcut=True)
    x = identity_Block(x, nb_filter=16, kernel_size=5, strides=1, with_conv_shortcut=False)

    x = identity_Block(x, nb_filter=32, kernel_size=5, strides=3, with_conv_shortcut=True)
    x = identity_Block(x, nb_filter=32, kernel_size=5, strides=1, with_conv_shortcut=False)

    x = identity_Block(x, nb_filter=32, kernel_size=5, strides=4, with_conv_shortcut=True)
    x = identity_Block(x, nb_filter=32, kernel_size=5, strides=1, with_conv_shortcut=False)

    x = identity_Block(x, nb_filter=64, kernel_size=5, strides=3, with_conv_shortcut=True)
    x = identity_Block(x, nb_filter=64, kernel_size=5, strides=1, with_conv_shortcut=False)
    x = identity_Block(x, nb_filter=64, kernel_size=5, strides=1, with_conv_shortcut=False)

    x = AveragePooling1D(pool_size=1)(x)
    x = Flatten()(x)
    x = Dense(2, activation='softmax')(x)

    model = keras.models.Model(inputs=input1,outputs=x)
    print(model.summary())
    # plot_model(model, to_file='./model_classifier.png', show_shapes=True)
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    # binary_crossentropy categorical_crossentropy
    return model

def identity_Block(inpt, nb_filter, kernel_size, strides, with_conv_shortcut=True):
    if with_conv_shortcut:
        x = Conv1d_BN(inpt, nb_filter=nb_filter, kernel_size=kernel_size, strides=strides, padding='same')
        x = Conv1d_BN(x, nb_filter=nb_filter, kernel_size=kernel_size, strides=1, padding='same')
        shortcut = Conv1d_BN(inpt, nb_filter=nb_filter, kernel_size=kernel_size, strides=strides, padding='same')
        x = add([x, shortcut])
        return x
    else:
        x = Conv1d_BN(inpt, nb_filter=nb_filter, kernel_size=kernel_size, strides=1, padding='same')
        x = Conv1d_BN(x, nb_filter=nb_filter, kernel_size=kernel_size, strides=1, padding='same')
        x = add([x, inpt])
        return x

def Conv1d_BN(x, nb_filter, kernel_size, strides, padding='same', name=None):
    if name is not None:
        bn_name = name + '_bn'
        conv_name = name + '_conv'
    else:
        bn_name = None
        conv_name = None

    x = Conv1D(nb_filter, kernel_size, padding=padding, strides=strides, activation='relu', name=conv_name)(x)
    x = BatchNormalization(axis=1, name=bn_name)(x)
    return x


def visual(model, data, num_layer=1):
    # data:image array
    # layer:layer n_outout
    layer = keras.backend.function([model.layers[0].input], [model.layers[num_layer].output])
    f1 = layer([data])[0]
    print(f1.shape)
    num = f1.shape[-1]
    print(num)
    plt.figure(figsize=(8, 8))
    for i in range(num):
        plt.subplot(int(np.ceil(np.sqrt(num))), int(np.ceil(np.sqrt(num))), i + 1)
        plt.imshow(f1[:, :, i] * 255, cmap='gray')
        plt.axis('off')
    plt.show()


# cobfusion matrix
def plot_confusion_matrix(cm, classes, title='Confusion matrix', cmap=plt.cm.jet):
    sns.set()
    fig, ax = plt.subplots()
    sns.heatmap(cm, annot=True, fmt='g', ax=ax, cmap="YlGnBu",annot_kws={"fontsize":60})  # Colors: YlGnBu
    # ax.set_xlabel('Predicted Label')
    # ax.set_xlabel('Predicted Label')
    # plt.savefig(csvfile + 'confusion_matrix_ID' + '.png')
    plt.show()


classs = ['0','1'] #h
weights = class_weight.compute_class_weight('balanced',classes=np.unique(Y_train),y=Y_train[:,1].reshape(-1))
#parameters
estimator = KerasRegressor(build_fn=resnet_34, validation_split=0.1, epochs=250, batch_size=100, verbose=1 , workers=12,class_weight=weights)

estimator.fit(X_train, Y_train)

acc = estimator.model.history.history['accuracy']
val_acc = estimator.model.history.history['val_accuracy']
loss = estimator.model.history.history['loss']
val_loss = estimator.model.history.history['val_loss']
epochs = range(len(acc))

plt.figure(1)
plt.subplot(121)
plt.plot(epochs, acc, 'r', label='Training')
plt.plot(epochs, val_acc, 'b', label='Validation')
plt.title('Accuracy',fontsize=26)
# plt.legend(loc=(0,0),fontsize=26)

plt.subplot(122)
plt.plot(epochs, loss, 'r', label='Training')
plt.plot(epochs, val_loss, 'b', label='Validation')
plt.title('Loss',fontsize=26)
plt.legend(fontsize=22)
# plt.savefig(csvfile + 'training&validaiton' + '.png')
plt.show()

model_json = estimator.model.to_json()
with open(r"E:\\study\\FigureWeights\\422\\710\\model.json", 'w')as json_file:
    json_file.write(model_json)  # 权重不在json中,只保存网络结构
estimator.model.save_weights('E:\\study\\FigureWeights\\422\\710\\model.h5')

tic = time.time()

json_file = open(r"E:\\study\\FigureWeights\\422\\710\\model.json", "r")
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
loaded_model.load_weights("E:\\study\\FigureWeights\\422\\710\\model.h5")
print("loaded model from disk")
loaded_model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

print("The accuracy of the classification model:")
scores = loaded_model.evaluate(X_test, Y_test, verbose=0)
print('%s: %.2f%%' % (loaded_model.metrics_names[1], scores[1] * 100))

predicted = loaded_model.predict(X_test)
# predictedlable = predicted.argmax(axis=-1)
all_probs = predicted[:, 1]
all_y = Y_test.argmax(axis=-1)
toc = time.time()
shijian = toc-tic



fpr, tpr, threshold = roc_curve(all_y, all_probs, pos_label=1)  # 计算真正率和假正率
A_sub = []
A_sub.append(fpr)
A_sub.append(tpr)
A_sub.append(threshold)
A_result = pd.DataFrame(A_sub)
A_result.to_excel(csvfile +'_roc' + '.xlsx')



roc_auc = auc(fpr, tpr)  # auc
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
plt.savefig(csvfile + '_roc curve' + '.png')
plt.show()

# binary
all_probs = [1 if x>=th else x for x in all_probs]
all_probs = [0 if x<th else x for x in all_probs]
all_y = [x for x in all_y]

tn, fp, fn, tp = confusion_matrix(all_y, all_probs).ravel()
cm = confusion_matrix(all_y, all_probs, labels=None, sample_weight=None)
plot_confusion_matrix(cm, 'confusion_matrix.png', classs)
Sen1 = tp / (tp + fn)
Spe1 = tn / (fp + tn)
Acc1 = (tp+tn) / (tn+fp+fn+tp)


B_sub = (Sen1,Spe1,Acc1,shijian)
B_result = pd.DataFrame(B_sub)
B_result.to_excel(csvfile+'_metrics' + '.xlsx')

plt.figure()
plt.axis('off')
plt.text(0, 0.8, 'Sensitivity : '+str(round(Sen1, 4)),fontsize=36,family='DejaVu Sans')
plt.text(0, 0.6, 'Specificity : '+str(round(Spe1, 4)),fontsize=36,family='DejaVu Sans')
plt.text(0, 0.4, 'Accuracy : '+str(round(Acc1, 4)),fontsize=36,family='DejaVu Sans')
plt.text(0, 0.2, 'Time : '+str(round(shijian, 4))+' s',fontsize=36,family='DejaVu Sans')
plt.savefig(csvfile + '_metrics' + '.png')
plt.show()

# joblib.dump(clf, './test.pkl')

print('done')