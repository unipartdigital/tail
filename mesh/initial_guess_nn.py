import json
from keras.models import Sequential, model_from_json
from keras.layers import Dense, Dropout, Flatten, Conv2D, Reshape, Input,\
    Activation, SeparableConv2D, UpSampling2D, UpSampling3D, GaussianNoise, AlphaDropout
from keras import optimizers
# from keras.utils.np_utils import to_categorical
import numpy
from simulate import gen_dataset


def create_model():
    # Define and Compile
    model = Sequential()
    # model.add(Input(shape=(100, 100, 2)))
    # model.add(UpSampling3D(size=(2, 16, 64), input_shape=(100, 100, 2)))
    # model.add(Conv2D(64, (8, 8), padding='valid', input_shape=(100, 100, 2)))
    # model.add(Conv2D(64, (2, 2), strides=(1, 1), padding='valid', input_shape=(100, 100, 2)))
    # model.add(Activation('relu'))
    # model.add(GaussianNoise(1))
    # model.add(Activation('relu'))
    model.add(Dense(2500, kernel_initializer='RandomUniform', activation='relu', input_shape=(50, 50)))
    model.add(Flatten())
    model.add(AlphaDropout(0.3))
    model.add(Dense(2020, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1850, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1720, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1630, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1530, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1430, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1230, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(1030, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(830, kernel_initializer='RandomUniform', activation='relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(630, kernel_initializer='RandomUniform', activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(153, kernel_initializer='RandomUniform', activation='relu'))
    model.add(Reshape((51, 3), input_shape=(153,)))
    # model.add(Flatten()
    # sgd = optimizers.Adam(lr=0.0000001, decay=1e-8)#, amsgrad=True)
    sgd = optimizers.SGD(lr=0.00001, decay=1e-12, momentum=0.9, nesterov=True)
                         # , clipnorm=0.5, clipvalue=1)
    model.compile(loss='mean_squared_error', optimizer=sgd, metrics=['accuracy'])
    # model.compile(loss='mean_squared_error', optimizer=sgd, metrics=['categorical_accuracy'])
    # model.compile(loss='mean_squared_logarithmic_error' , optimizer='adam', metrics=['categorical_accuracy'])
    return model


def save_model(model, filename="model"):
    model_json = model.to_json()
    with open(filename+".json", "w") as json_file:
        json_file.write(model_json)
    model.save_weights(filename+'.h5')


def load_model(filename):
    with open(filename+'.json', 'r') as json_file:
        loaded_model = model_from_json(json_file.read())
    # load weights into new model
    loaded_model.load_weights(filename+".h5")
    print("Loaded model from disk")
    sgd = optimizers.SGD(lr=0.000001, decay=1e-12, momentum=0.9, nesterov=True)
    # , clipnorm=0.5, clipvalue=1)
    loaded_model.compile(loss='mean_squared_error', optimizer=sgd,
                  metrics=['accuracy'])
    return loaded_model


def load_dataset():

    def load2d(filename):
        # Load the dataset
        with open(filename, 'r') as file:
            data = json.loads(file.readline())
            # print(data)
        x = numpy.zeros((len(data), 50, 50, 2), dtype=numpy.float32)
        points = []
        for i, line in enumerate(data):
            for distance in line['distances']:
                # print(distance)
                x[i, distance[0], distance[1], :] = \
                    numpy.array(distance, dtype=numpy.float32)[2:]
            points.append(line['points'])
        points = numpy.array(points, dtype=numpy.float32)
        y = numpy.zeros((points.shape[0],51, 3), dtype=numpy.float32)
        # print(points.shape[0], points.shape[1], points.shape[2])
        # print(y.shape[0], y.shape[1], y.shape[2])
        y[:, 0:points.shape[1], :] = points[:, :, :]
        # print(x)
        # print(y)
        return x, y

    def load1d(filename):
        # Load the dataset
        with open(filename, 'r') as file:
            data = json.loads(file.readline())
            # print(data)
        x = numpy.zeros((len(data), 50, 50), dtype=numpy.float32)
        points = []
        for i, line in enumerate(data):
            for distance in line['distances']:
                # print(distance)
                x[i, distance[0], distance[1]] = \
                    numpy.array(distance, dtype=numpy.float32)[2]
            points.append(line['points'])
        points = numpy.array(points, dtype=numpy.float32)
        y = numpy.zeros((points.shape[0],51, 3), dtype=numpy.float32)
        # print(points.shape[0], points.shape[1], points.shape[2])
        # print(y.shape[0], y.shape[1], y.shape[2])
        y[:, 0:points.shape[1], :] = points[:, :, :]
        # print(x)
        # print(y)
        return x, y

    x_train, y_train = load1d('train.json')
    x_test, y_test = load1d('test.json')
    # num_classes = int(numpy.max(dataset[:, :1]) + 1)
    # y_train = to_categorical(y_train, num_classes)
    # y_test = to_categorical(y_test, num_classes)
    return [x_train, y_train, x_test, y_test]


def train_model():
    X, Y, x_test, y_test = load_dataset()
    model = create_model()#num_classes)
    model.fit(X, Y, epochs=80, batch_size=100, validation_data=(x_test, y_test))
    # Evaluate the model
    scores = model.evaluate(X, Y)
    print("%s: %.2f%%" % (model.metrics_names[1], scores[1]*100))
    score = model.evaluate(x_test, y_test, verbose=1)
    print(score)
    save_model(model, 'test_model1')


def continuouse_model_training():
    # model = load_model('test_model1')  # num_classes)
    model = create_model()  # num_classes)
    i = 0
    while 1:
    # for i in range(200):
        X, Y, x_test, y_test = load_dataset()
        model.fit(X, Y, epochs=3, batch_size=100, validation_data=(x_test, y_test))
        # Evaluate the model
        scores = model.evaluate(X, Y)
        print("%s: %.2f%%" % (model.metrics_names[1], scores[1] * 100))
        score = model.evaluate(x_test, y_test, verbose=1)
        print(score, 'Iteration ', i)
        i += 1
        gen_dataset()
        save_model(model, 'test_model1')


if __name__ == "__main__":
    seed = 7
    numpy.random.seed(seed)

    import tensorflow as tf
    from keras.backend.tensorflow_backend import set_session
    config = tf.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = 0.95
    config.gpu_options.visible_device_list = "0"
    config.gpu_options.allow_growth = True
    set_session(tf.Session(config=config))


    continuouse_model_training()