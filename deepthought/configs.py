import os
from collections import OrderedDict

config = OrderedDict()

def abspath(path):
    return os.path.abspath(path)

def read_env_value(name, default):
    if name in os.environ:
        value = os.environ[name]
    else:
        value = default
    return value

MM_DIR = {
            "name" : "MM_DIR", 
            "default" : "C:\Program Files\Micro-Manager-2.0gamma"
}
MM_CONFIG = {
                "name" : "MM_CONFIG",
                "default" : "./mmconfigs/Bright_Star.cfg"
}

config["mm_dir"] = abspath(read_env_value(**MM_DIR))
config["mm_config"] = abspath(read_env_value(**MM_CONFIG))
