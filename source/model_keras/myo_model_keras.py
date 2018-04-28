import glob
import os

os.environ['KERAS_BACKEND'] = 'tensorflow'  # 也可以使用 tensorflow
# os.environ['THEANO_FLAGS']='floatX=float32,device=cuda,exception_verbosity=high'
os.environ['THEANO_FLAGS'] = 'floatX=float32,device=cuda,optimizer=fast_compile'
#os.environ["CUDA_VISIBLE_DEVICES"] = "7"

import keras.backend as K

K.set_image_data_format('channels_last')

import time
from keras.models import Sequential, Model
from keras.layers import Conv2D, ZeroPadding2D, BatchNormalization, Input, LSTM, Concatenate, Dense
from keras.layers import Conv2DTranspose, Reshape, Activation, Cropping2D, Flatten
from keras.layers.advanced_activations import LeakyReLU
from keras.activations import relu
from keras.initializers import RandomNormal
from keras.datasets import mnist
from urllib.request import urlretrieve
from keras.optimizers import RMSprop, SGD, Adam

#from read_data import *
from load_data import DataLoader

'''
Model structure

Input : (100) Vector
Output : (64, 64, 1) image

Generator
100 -> 256
256 -> 16 x 16
16 x 16 -> 32 x 32
32 x 32 -> 64 x 64
64 x 64 -> 128 x 128

Discriminator
128 x 128 -> 64 x 64
64 x 64 -> 32 x 32
32 x 32 -> 16 x 16
16 x 16 -> 8 x 8
8 x 8 -> 64
64 -> 32 (16, 10)

'''
loader = DataLoader(emg_data_path='../data_preprocessing/DataLoader/Sample_data/emg.csv', image_path='../data_preprocessing/DataLoader/Sample_data/hand_images/')

conv_init = RandomNormal(0, 0.02)
gamma_init = RandomNormal(1., 0.02)

def make_lstm_layer(lstm_size):

    lstm_input = Input(shape=lstm_size)
    lstm_layer = LSTM(80, input_shape=lstm_size)(lstm_input)
    lstm_layer = Activation(activation='tanh')(lstm_layer)

    print("lstm : ", type(lstm_layer))
    print("lstm : ", lstm_layer)

    return Model(inputs=lstm_input, outputs=lstm_layer)

def generative_model(noise_size):
    #lstm_layer = Input(shape=lstm_size)
    #noise_input = Input(shape=(noise_size,))
    temp_input = Input(shape=(1, 1))

    print("G model lstm : ", type(lstm_layer), lstm_layer)
    #lstm_layer = (lstm_layer)(temp_input)
    _ = Concatenate(axis=-1)([lstm_layer, noise_input])
    print(" _ : ", _)
    _ = Dense(256, input_shape=(100, ), activation='relu', bias_initializer='glorot_normal', kernel_initializer='glorot_normal')(_)
    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Reshape((16, 16, 1), input_shape=(256, ))(_)

    _ = Conv2D(filters=128, kernel_size=(2, 2), padding='same', kernel_initializer=conv_init, input_shape=(16, 16, 1))(_)
    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Activation(activation='relu')(_)

    _ = Conv2DTranspose(filters=256, kernel_size=(2, 2), strides=2, kernel_initializer=conv_init, input_shape=(16, 16, 128))(_)
    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Activation(activation='relu')(_)

    _ = Conv2DTranspose(filters=512, kernel_size=(2, 2), strides=2, kernel_initializer=conv_init, input_shape=(32, 32, 256))(_)
    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Activation(activation='relu')(_)

    _ = Conv2DTranspose(filters=256, kernel_size=(2, 2), strides=2, kernel_initializer=conv_init, input_shape=(64, 64, 512))(_)
    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Activation(activation='relu')(_)

    _ = Conv2D(filters=1, kernel_size=(128, 128), padding='same', kernel_initializer=conv_init, input_shape=(128, 128, 256))(_)
    _ = Activation(activation='relu')(_)

    return Model(inputs=[lstm_layer, noise_input], outputs=_)

def discriminative_model(image_size, image_channel):

    _ = inputs = Input(shape=(image_size, image_size, image_channel))

    _ = Conv2D(filters=256, kernel_size=(2, 2), strides=2, padding='same', input_shape=(128, 128, 1), kernel_initializer=conv_init)(_)
    _ = LeakyReLU(alpha=0.2)(_)

    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Conv2D(filters=512, kernel_size=(2, 2), strides=2, padding='same', input_shape=(64, 64, 256), kernel_initializer=conv_init)(_)
    _ = LeakyReLU(alpha=0.2)(_)

    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Conv2D(filters=256, kernel_size=(2, 2), strides=2, padding='same', input_shape=(32, 32, 512), kernel_initializer=conv_init)(_)
    _ = LeakyReLU(alpha=0.2)(_)

    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Conv2D(filters=128, kernel_size=(2, 2), strides=2, padding='same', input_shape=(16, 16, 256), kernel_initializer=conv_init)(_)
    _ = LeakyReLU(alpha=0.2)(_)

    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Conv2D(filters=128, kernel_size=(2, 2), strides=2, padding='same', input_shape=(8, 8, 128), kernel_initializer=conv_init)(_)
    _ = LeakyReLU(alpha=0.2)(_)

    _ = BatchNormalization(axis=1, gamma_initializer=gamma_init)(_)
    _ = Conv2D(filters=1, kernel_size=(2, 2), strides=1, padding='same', input_shape=(4, 4, 128), kernel_initializer=conv_init)(_)
    #_ = LeakyReLU(alpha=0.2)(_)

    _ = Flatten()(_)
    outputs = Activation(activation='sigmoid')(_)

    return Model(inputs=inputs, outputs=outputs)

lstm_size = (300, 16)
#print("lstm size : ", lstm_size)
noise_size = 20
image_size = 128
input_size = 100
image_channel = 1
learning_rate = 2e-4

lstm_input = Input(shape=lstm_size)
noise_input = Input(shape=(noise_size,))
real_image = Input(shape=(image_size, image_size, image_channel))

net_lstm = make_lstm_layer(lstm_size)
net_lstm.summary()

#lstm_input = net_lstm.input
lstm_layer = net_lstm(lstm_input)

print("net lstm output : ", net_lstm.get_output_at(0))

net_g = generative_model(noise_size)
net_g.summary()

net_d = discriminative_model(image_size, image_channel)
net_d.summary()

#noise_input = net_g.input
#real_image = net_d.input

print(noise_input)

print("make lstm output : ", type(lstm_layer))
print("make lstm output : ", lstm_layer)

fake_image = net_g(noise_input)
net_d_fake = net_d(net_lstm.get_output_at(0), fake_image)
net_d_real = net_d(net_lstm.get_output_at(0), real_image)

loss_fn = lambda output, target: -K.mean(K.log(output + 1e-12) * target + K.log(1 - output + 1e-12) * (1 - target))

loss_lstm = loss_fn(lstm_layer, K.zeros_like(lstm_layer))
loss_d_real = loss_fn(net_d_real, K.ones_like(net_d_real))
loss_d_fake = loss_fn(net_d_fake, K.zeros_like(net_d_fake))
loss_g_noise = loss_fn(net_d_fake, K.ones_like(net_d_fake))

loss_d = loss_d_real + loss_d_fake
training_updates = Adam(lr=learning_rate, beta_1=0.5).get_updates(net_d.trainable_weights, [], loss_d)
net_d_train = K.function([real_image], [loss_d / 2.0], training_updates)

loss_g = loss_g_noise + loss_lstm
training_updates = Adam(lr=learning_rate, beta_1=0.5).get_updates(net_g.trainable_weights, [], loss_g)
net_g_train = K.function([noise_input], [loss_g], training_updates)

'''
myo_data = loader.get_emg_datas(1)
myo_data = myo_data.reshape(myo_data[0, :, 0].size, myo_data[0, 0, :].size)

print("myo data : ", myo_data)
print("myo data size : ", myo_data[:, 0].size, myo_data[0, :].size)


loader = DataLoader(emg_data_path='./Sample_data/emg.csv', image_path='./Sample_data/hand_images/')
print('Total image number :', loader.total_image_number, 'Total EMG seconds :', loader.total_emg_seconds)

# Get next EMG datas or Images
test_emg = loader.get_next_emgs(1)
test_image = loader.get_next_images(1)

print(type(test_emg), test_emg.shape)
print(type(test_image), test_image.shape)

'''

epoch = 50
i = 0
time_0 = time.time()
err_d = err_g = 0
err_d_sum = 0
err_g_sum = 0
batch_size = loader.total_image_number

print(batch_size)
print('Total image number :', loader.total_image_number, 'Total EMG seconds :', loader.total_emg_seconds)

while i < epoch:
    j = 0

    #data = data.reshape(data[0, :, 0].size, data[0, 0, :].size)

    while j < batch_size:
        train_image = loader.get_next_images(1)
        data = loader.get_next_emgs(1)

        print(type(train_image), train_image.shape)
        print(type(data), data.shape)
        j += 1

        #err_d, = net_d_train[train_image]
        #err_d_sum += err_d

    i += 1



