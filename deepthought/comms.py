"""Patterns for communication protocol between microservices or modules to interact with different objects"""
import rpyc
from rpyc.utils.server import ThreadedServer


def server(object_, port, *args, **kwargs):
    s = ThreadedServer(object_, hostname="", port=port, auto_register=None,
                         protocol_config={"allow_all_attrs": True, 
                                          "allow_pickle" : True,
                                        }
                      )
    print(f"Starting server in: {port}")
    return s

def client(addr, port, *args, **kwargs):
    obj = rpyc.connect(addr, port, config={
        "allow_all_attrs": True, "allow_pickle" : True
    })
    
    print(f"Connected to server in {addr}:{port}")
    return obj.root

