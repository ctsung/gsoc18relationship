from concurrent import futures

import time
import grpc
import argparse
import pickle
import tensorflow as tf

from feedhandling import feed_handling_pb2
from feedhandling import feed_handling_pb2_grpc
from tflearning import tf_learning_pb2
from tflearning import tf_learning_pb2_grpc
from tflearning.NN import NN
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2
from tensorflow.python.framework import tensor_util
import get_training_data

_ONE_DAY_IN_SECONDS = 60 * 60 * 24
tf.app.flags.DEFINE_string('server', 'localhost:9000', 'PredictionService host:port')
FLAGS = tf.app.flags.FLAGS

def train_model():
    nn_instance = NN("./objects.p", label_length=20)
    skf = nn_instance.split_train_test(3, 0)

    for train_index, test_index in skf:
        nn_instance.prepare_data(train_index, test_index)
        nn_instance.train()

    return nn_instance

def convert_to_name(labels):
    label = ['CryptoRansom', 'apt1', 'athena_variant', 'betabot', 'blackshades', 'citadel_krebs', 'darkcomet', 'darkddoser', 'dirtjumper', 'expiro', 'gamarue', 'ghostheart2', 'locker', 'machbot', 'mediyes', 'nitol', 'pushdo', 'shylock', 'simda', 'yoyoddos2', 'CIA Malware', 'Hijacker', 'Trojan', 'Zeus offshoot', 'Password stealing tool', 'DDoS Bot', 'Virus', 'Worm', 'Botnet']

    names = []

    for i in labels:
        names.append(label[i])

    return names

def get_hidden_features(self, hostport, mlp_features, cnn_features):
    host, port = hostport.split(':')
    channel = implementations.insecure_channel(host, int(port))
    stub = prediction_service_pb2.beta_create_PredictionService_stub(channel)

    request = predict_pb2.PredictRequest()
    request.model_spec.name = 'malware'
    request.model_spec.signature_name = tf.saved_model.signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY

    request.inputs['mlp_features'].CopyFrom(tf.contrib.util.make_tensor_proto(mlp_features, shape=mlp_features.shape))
    request.inputs['cnn_features'].CopyFrom(tf.contrib.util.make_tensor_proto(cnn_features, shape=cnn_features.shape))
    request.inputs['keep_prob'].CopyFrom(tf.contrib.util.make_tensor_proto(1.0))

    response = stub.Predict(request, 5.0)

    return tensor_util.MakeNdarray(response.outputs['label'])


class TFLearningServicer(tf_learning_pb2_grpc.TFLearningServicer):
    def __init__(self, verbose):
        self.verbose = verbose

        # start tensorflow_model_server

    def PredictLabel(self, request, context):
        if self.verbose:
            print('[Request] PredictLabel()')
            print('[Info] Preparing malware features to predict the label')

        X_objdump = preprocessing.MinMaxScaler().fit_transform(request.features_cuckoo)
        X_peinfo = preprocessing.MinMaxScaler().fit_transform(request.features_objdump)
        X_richheader = preprocessing.MinMaxScaler().fit_transform(request.features_peinfo)
        mlp_features = np.concatenate((X_objdump, X_peinfo, X_richheader), axis=1).astype(np.float32)
        cnn_features = np.array(request.features_richheader).astype(np.int32)

        if self.verbose:
            print('[Info] Predicting the label')

        labels = get_hidden_features(FLAGS.server, mlp_features, cnn_features)

        for i in labels:
            yield tf_learning_pb2.Labels(labels=labels)

        if self.verbose:
            print('[Info] Predicted label sent!')

    def GetRelationships(self, request, context):
        if self.verbose:
            print('[Request] GetRelationships()')
            print('[Info] Preparing malware relationships')

        tree = pickle.load(open('ftree.p', 'rb'))
        sha256 = pickle.load(open('sha256.p', 'rb'))
        hidden_features = pickle.load(open('hf.p', 'rb'))
        labels = pickle.load(open('labels.p', 'rb'))

        if request.sha256 in sha256:
            j = sha256.index(request.sha256)
            dist, ind = tree.query(hidden_features[j,:].reshape(1, -1), k=2000)

            yield tf_learning_pb2.Relationships(sha256=sha256[j], labels=convert_to_name(labels[j]), distance=0)
            for i in range(len(ind[0])):
                if j != ind[0][i] and set(labels[j]) == set(labels[ind[0][i]]):
                    yield tf_learning_pb2.Relationships(sha256=sha256[ind[0][i]], labels=convert_to_name(labels[ind[0][i]]), distance=dist[0][i])

            if self.verbose:
                print('[Info] Relationship sent!')

    def TrainModel(self, request, context):
        if self.verbose:
            print('[Request] TrainModel()')
            print('[Info] Start fetching training data')

        get_training_data.run()

        if self.verbose:
            print('[Info] Training data fetched!')
            print('[Info] Start training the model')

        nn_instance = train_model()
        nn_instance.save()

        if self.verbose:
            print('[Info] Training done!')

        # restart tensorflow_model_server

        return tf_learning_pb2.Empty()

    def Echo(self, request, context):
        if self.verbose:
            print('[Request] Echo(%s)' % request.msg)

        return tf_learning_pb2.Foo(msg=request.msg)

def serve(verbose):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tf_learning_pb2_grpc.add_TFLearningServicer_to_server(TFLearningServicer(verbose), server)
    server.add_insecure_port('[::]:9091')
    server.start()

    if verbose:
        print('[Info] Tensorflow learning server init')

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='python tfl_server.py', description='Tensorflow learning server')
    parser.add_argument('-v', '--verbose', help='Verbose mode', action='store_true')
    args = parser.parse_args()

    serve(args.verbose)
