"""Patterns for communication protocol between microservices or modules to interact with different objects"""

import zerorpc


def serve_object(object_, address):
    """expose an object in an address for get_object to connect to"""
    server = zerorpc.Server(object_)
    server.bind(address)
    return server


def get_object(address):
    """connect to an object served by serve_object"""
    object_ = zerorpc.Client()
    object_.connect(address)
    return object_
