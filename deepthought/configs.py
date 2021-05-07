from collections import OrderedDict
import os

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
    "name": "MM_DIR",
    "default": "C:\Program Files\Micro-Manager-2.0gamma"
}
MM_CONFIG = {
    "name": "MM_CONFIG",
    "default": "./mmconfigs/Bright_Star.cfg"
}
MM_SERVER = {
    "name": "MM_SERVER",
    "default": "localhost",
}
config["mm_dir"] = abspath(read_env_value(**MM_DIR))
config["mm_config"] = abspath(read_env_value(**MM_CONFIG))
config["mm_server"] = {"addr": read_env_value(**MM_SERVER), "port": 18861}
store_disk = True
# feature toggle
