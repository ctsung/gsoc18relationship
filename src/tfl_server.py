from concurrent import futures
import time
import grpc
import argparse

from feedhandling import feed_handling_pb2
from feedhandling import feed_handling_pb2_grpc
from tflearning import tf_learning_pb2
from tflearning import tf_learning_pb2_grpc
import get_training_data

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class TFLearningServicer(tf_learning_pb2_grpc.TFLearningServicer):
    def __init__(self, verbose):
        self.verbose = verbose

        # start tensorflow_model_server

    def PredictLabel(self, request, context):
        pass

    def GetRelationships(self, request, context):
        pass

    def TrainModel(self, request, context):
        if self.verbose:
            print('[Request] TrainModel()')
            print('[Info] Start fetching training data')

        get_training_data.run()

        if self.verbose:
            print('[Info] Training data fetched!')
            print('[Info] Start training the model')

        # train the model

        if self.verbose:
            print('[Info] Training done!')

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
