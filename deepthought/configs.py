from collections import OrderedDict 
import os

config = OrderedDict()

if os.name == 'nt':
    config["mm_dir"] = "C:\Program Files\Micro-Manager-2.0gamma"
elif os.name == "posix":
    config["mm_dir"] = "/home/dna/lab/software/micromanager/lib/micro-manager"

config["mm_config"] = "/mmconfigs/demo.cfg"
config["mm_server"] = {"addr" : "localhost", "port" : 18861}