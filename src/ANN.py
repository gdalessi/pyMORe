import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from tensorflow.python.keras.models import Sequential
from tensorflow.python.keras.layers import Dense
import os 
import os.path
from keras.callbacks import EarlyStopping 
from keras.callbacks import ModelCheckpoint 
from keras.layers import LeakyReLU


class MLP_classifier:
    def __init__(self, X, Y, n_neurons, ReLU=True, save=False):
        self.X = X
        self.Y = Y
        self.neurons = n_neurons
        if ReLU:
            activation = 'relu'
            self.activation = activation
        else:
            LR = LeakyReLU(alpha=0.0001)
            LR.__name__ = 'relu'    #just to fool python change the name of the LeakyRelu
            activation = LR 
            self.activation = activation
        self.save_txt = save


    @staticmethod
    def set_hard_parameters():
        activation_output = 'softmax'
        batch_size_ = 64
        n_epochs_ = 1000 # it's a lot but we will have early stopping anyway
        path_ = os.getcwd()
        monitor_early_stop= 'val_loss'
        optimizer_= 'adam'
        patience_= 5
        loss_classification_= 'categorical_crossentropy'
        metrics_classification_= 'accuracy'

        return activation_output, batch_size_, n_epochs_, path_, monitor_early_stop, optimizer_, patience_, loss_classification_, metrics_classification_

    def fit_network(self):
        X_train, X_test, y_train, y_test = train_test_split(self.X, self.Y, test_size=0.3)
        input_dimension = self.X.shape[1]
        number_of_classes = self.Y.shape[1]
        activation_output, batch_size_, n_epochs_, path_, monitor_early_stop, optimizer_, patience_, loss_classification_, metrics_classification_ = MLP_classifier.set_hard_parameters()

        classifier = Sequential()
        classifier.add(Dense(self.neurons, activation=self.activation, kernel_initializer='random_normal', input_dim=input_dimension))
        classifier.add(Dense(number_of_classes, activation=activation_output, kernel_initializer='random_normal'))
        classifier.summary()

        earlyStopping = EarlyStopping(monitor=monitor_early_stop, patience=patience_, verbose=1, mode='min')
        mcp_save = ModelCheckpoint(filepath=path_ + '/best_weights.h5', verbose=1, save_best_only=True, monitor=monitor_early_stop, mode='min')

        classifier.compile(optimizer =optimizer_,loss=loss_classification_, metrics =[metrics_classification_])
        history = classifier.fit(X_train, y_train, validation_data=(X_test, y_test), batch_size=batch_size_, epochs=n_epochs_, callbacks=[earlyStopping, mcp_save])

        # Summarize history for accuracy
        plt.plot(history.history['acc'])
        plt.plot(history.history['val_acc'])
        plt.title('Model accuracy')
        plt.ylabel('Accuracy')
        plt.xlabel('Epoch number')
        plt.legend(['Train', 'Test'], loc='lower right')
        plt.show()

        # Summarize history for loss
        plt.plot(history.history['loss'])
        plt.plot(history.history['val_loss'])
        plt.title('Model loss')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Test'], loc='upper right')
        plt.show()

        if self.save_txt:

            first_layer_weights = classifier.layers[0].get_weights()[0]
            first_layer_biases  = classifier.layers[0].get_weights()[1]
            class_layer_weights = classifier.layers[1].get_weights()[0]
            class_layer_biases = classifier.layers[1].get_weights()[1]
            
            np.savetxt(path_+ '/weightsHL1.txt', first_layer_weights)
            np.savetxt(path_+ '/biasHL1.txt', first_layer_biases)
            np.savetxt(path_+ '/weightsCL.txt', class_layer_weights)
            np.savetxt(path_+ '/biasCL.txt', class_layer_biases)
        
        test = classifier.predict(self.X)
        return test


class Autoencoder:
    def __init__(self, X, encoding_dimension, ReLU=True, save=False):
        self.X = X
        self.encoding_dimension = encoding_dimension
        if ReLU:
            activation_function = 'relu'
            self.activation_function = activation_function
        else:
            LR = LeakyReLU(alpha=0.0001)
            LR.__name__ = 'relu'    #just to fool python change the name of the LeakyRelu
            activation_function = LR 
            self.activation_function = activation_function
        self.save_txt = save

    @staticmethod
    def set_hard_parameters():
        activation_output = 'linear'
        batch_size_ = 64
        n_epochs_ = 1000 # it's a lot but we will have early stopping anyway
        path_ = os.getcwd()
        monitor_early_stop= 'val_loss'
        optimizer_= 'adam'
        patience_= 5
        loss_function_= 'mse'
        metrics_= 'accuracy'

        return activation_output, batch_size_, n_epochs_, path_, monitor_early_stop, optimizer_, patience_, loss_function_, metrics_

    
    def fit(self):
        from keras.layers import Input, Dense
        from keras.models import Model
        
        input_dimension = self.X.shape[1]
        X_train, X_test, y_train, y_test = train_test_split(self.X, self.X, test_size=0.3)
        
        activation_output, batch_size_, n_epochs_, path_, monitor_early_stop, optimizer_, patience_, loss_function_, metrics_ = Autoencoder.set_hard_parameters()

        input_data = Input(shape=(input_dimension,))
        encoded = Dense(self.encoding_dimension, activation=self.activation_function)(input_data)
        decoded = Dense(input_dimension, activation=activation_output)(encoded)
        
        autoencoder = Model(input_data, decoded)

        encoder = Model(input_data, encoded)
        encoded_input = Input(shape=(self.encoding_dimension,))
        decoder_layer = autoencoder.layers[-1]
        decoder = Model(encoded_input, decoder_layer(encoded_input))

        autoencoder.compile(optimizer=optimizer_, loss=loss_function_)

        earlyStopping = EarlyStopping(monitor=monitor_early_stop, patience=patience_, verbose=1, mode='min')
        history = autoencoder.fit(X_train, X_train, validation_data=(X_test, X_test), epochs=n_epochs_, batch_size=batch_size_, shuffle=True, callbacks=[earlyStopping])

        plt.plot(history.history['loss'])
        plt.plot(history.history['val_loss'])
        plt.title('Model loss')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Test'], loc='upper right')
        plt.show()

        encoded_X = encoder.predict(self.X)

        if self.save_txt:
            first_layer_weights = encoder.get_weights()[0]
            first_layer_biases  = encoder.get_weights()[1]

            np.savetxt(path_+ 'AEweightsHL1.txt', first_layer_weights)
            np.savetxt(path_+ 'AEbiasHL1.txt', first_layer_biases)

            np.savetxt(path_+ 'Encoded_matrix.txt', encoded_X)

class MLP_regressor:
    def __init__(self, X, Y, n_neurons, ReLU=True, save=False):
        self.X = X
        self.Y = Y
        self.neurons = n_neurons
        if ReLU:
            activation_function = 'relu'
            self.activation_function = activation_function
        else:
            LR = LeakyReLU(alpha=0.0001)
            LR.__name__ = 'relu'    #just to fool python change the name of the LeakyRelu
            activation_function = LR 
            self.activation_function = activation_function
        self.save_txt = save

    @staticmethod
    def set_hard_parameters():
        activation_output = 'linear'
        batch_size_ = 64
        n_epochs_ = 1000 # it's a lot but we will have early stopping anyway
        path_ = os.getcwd()
        monitor_early_stop= 'mean_squared_error'
        optimizer_= 'adam'
        patience_= 5
        loss_function_= 'mean_squared_error'
        metrics_= 'mse'

        return activation_output, batch_size_, n_epochs_, path_, monitor_early_stop, optimizer_, patience_, loss_function_, metrics_


    def fit_network(self):
        input_dimension = self.X.shape[1]
        output_dimension = self.Y.shape[1]

        X_train, X_test, y_train, y_test = train_test_split(self.X, self.Y, test_size=0.3)

        activation_output, batch_size_, n_epochs_, path_, monitor_early_stop, optimizer_, patience_, loss_function_, metrics_ = MLP_regressor.set_hard_parameters()

        model = Sequential()
        model.add(Dense(self.neurons, input_dim=input_dimension, kernel_initializer='normal', activation=self.activation_function)) 
        model.add(Dense(output_dimension, activation=activation_output))
        model.summary()

        earlyStopping = EarlyStopping(monitor=monitor_early_stop, patience=patience_, verbose=0, mode='min')
        mcp_save = ModelCheckpoint(filepath=path_+ '/best_weights2c.h5', verbose=1, save_best_only=True, monitor=monitor_early_stop, mode='min')
        model.compile(loss=loss_function_, optimizer=optimizer_, metrics=[metrics_])
        history = model.fit(X_train, y_train, batch_size=batch_size_, epochs=n_epochs_, verbose=1, validation_data=(X_test, y_test), callbacks=[earlyStopping, mcp_save])

        plt.plot(history.history['loss'])
        plt.plot(history.history['val_loss'])
        plt.title('Model loss')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Test'], loc='upper right')
        plt.show()

        model.load_weights(path_+ '/best_weights2c.h5')

        test = model.predict(self.X)

        if self.save_txt:

            first_layer_weights = model.layers[0].get_weights()[0]
            first_layer_biases  = model.layers[0].get_weights()[1]
            out_layer_weights = model.layers[1].get_weights()[0]
            out_layer_biases = model.layers[1].get_weights()[1]

            np.savetxt(path_+ '/weightsHL1.txt', first_layer_weights)
            np.savetxt(path_+ '/biasHL1.txt', first_layer_biases)
            np.savetxt(path_+ '/weightsCL.txt', out_layer_weights)
            np.savetxt(path_+ '/biasCL.txt', out_layer_biases)

        return test