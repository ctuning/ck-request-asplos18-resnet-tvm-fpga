# some standard imports
import nnvm
import tvm
from nnvm.compiler import graph_attr
import vta
import os
import numpy as np
from PIL import Image
import pickle
import json
import logging
import wget
from tvm.contrib import graph_runtime, rpc, util
import sys #FGG

factor = 16
host = "cknowledge.ddns.net"
port = 9091
verbose = False
# only run fpga component, mark non-conv ops as nop
debug_fpga_only = False

# FGG: get file to classify from CMD
argv=sys.argv
TEST_FILE=argv[1]

# FGG: set timers
import time
timers={}

# FGG: set model files via CK env
CATEG_FILE = os.environ['CK_ENV_MODEL_VTA_MODEL_LABELS_FULL'] # 'synset.txt'
RESNET_GRAPH_FILE = os.environ['CK_ENV_MODEL_VTA_MODEL_FULL'] # 'quantize_graph.json'
RESNET_PARAMS_FILE = os.environ['CK_ENV_MODEL_VTA_MODEL_WEIGHTS_FULL'] # 'quantize_params.pkl'
BITSTREAM_FILE = os.environ['CK_ENV_MODEL_VTA_MODEL_BIT_FULL'] #' vta.bit'
BITSTREAM_FILENAME = os.environ['CK_ENV_MODEL_VTA_MODEL_BIT'] #' vta.bit'

STAT_REPEAT=os.environ.get('STAT_REPEAT','')
if STAT_REPEAT=='' or STAT_REPEAT==None:
   STAT_REPEAT=10
STAT_REPEAT=int(STAT_REPEAT)

# Program the FPGA remotely
dt=time.time()
assert tvm.module.enabled("rpc")
remote = rpc.connect(host, port)
remote.upload(BITSTREAM_FILE, BITSTREAM_FILENAME)
fprogram = remote.get_function("tvm.contrib.vta.init")
fprogram(BITSTREAM_FILENAME)
timers['execution_time_upload_bitstream']=time.time()-dt

if verbose:
    logging.basicConfig(level=logging.INFO)

# Change to -device=tcpu to run cpu only inference.
target = "llvm -device=vta"

dt=time.time()
synset = eval(open(os.path.join(CATEG_FILE)).read())
image = Image.open(os.path.join(TEST_FILE)).resize((224, 224))
timers['execution_time_load_image']=time.time()-dt

def transform_image(image):
    image = np.array(image) - np.array([123., 117., 104.])
    image /= np.array([58.395, 57.12, 57.375])
    image = image.transpose((2, 0, 1))
    image = image[np.newaxis, :]
    return image

def mark_nop(graph, conv_layer=-1, skip_conv_layer=()):
    """Helper function to mark certain op as nop

    Useful to debug performance issues.
    """
    jgraph = json.loads(graph.json())
    counter = 0
    for nid, node in enumerate(jgraph["nodes"]):
        op_name = node["op"]
        if op_name != "tvm_op":
            continue
        attrs = node["attrs"]
        node_name = node["name"]
        func_name = attrs["func_name"]
        if func_name.find("quantized_conv2d") != -1:
            if conv_layer >= 0:
                if counter != conv_layer:
                    attrs["func_name"] = "__nop"
            if counter in skip_conv_layer:
                attrs["func_name"] = "__nop"
            counter += 1
        else:
            if conv_layer >= 0:
                attrs["func_name"] = "__nop"
            attrs["func_name"] = "__nop"
        if attrs["func_name"] != "__nop":
            print("Run function %s"% func_name)
    graph = nnvm.graph.load_json(json.dumps(jgraph))
    return graph

dt=time.time()
x = transform_image(image)
timers['execution_time_transform_image']=time.time()-dt
print('x', x.shape)

######################################################################
# now compile the graph
import nnvm.compiler
np.random.seed(0)
sym = nnvm.graph.load_json(
    open(os.path.join(RESNET_GRAPH_FILE)).read())
params = pickle.load(
    open(os.path.join(RESNET_PARAMS_FILE)))

dt=time.time()
shape_dict = {"data": x.shape}
dtype_dict = {"data": 'float32'}
shape_dict.update({k: v.shape for k, v in params.items()})
dtype_dict.update({k: str(v.dtype) for k, v in params.items()})

graph = nnvm.graph.create(sym)
graph_attr.set_shape_inputs(sym, shape_dict)
graph_attr.set_dtype_inputs(sym, dtype_dict)
graph = graph.apply("InferShape").apply("InferType")

dtype = "float32"
sym = vta.graph.remove_stochastic(sym)
sym = vta.graph.clean_cast(sym)
sym = vta.graph.clean_conv_fuse(sym)
if "vta" in target:
    sym = vta.graph.pack(sym, shape_dict, factor)

graph_attr.set_shape_inputs(sym, shape_dict)
sym = sym.apply("InferShape")
graph_attr.set_dtype_inputs(sym, dtype_dict)
sym = sym.apply("InferType")
timers['execution_time_prepare_graph']=time.time()-dt

with nnvm.compiler.build_config(opt_level=3):
    bdict = {}
    if "vta" not in target:
        bdict = {"add_lower_pass": []}
    else:
        bdict = {"add_lower_pass": vta.debug_mode(0)}
    with tvm.build_config(**bdict):
        graph, lib, params = nnvm.compiler.build(
            sym, target, shape_dict, dtype_dict,
            params=params)

print ("connecting ...")
dt=time.time()
remote = rpc.connect(host, port)
temp = util.tempdir()
lib.save(temp.relpath("graphlib.o"))
remote.upload(temp.relpath("graphlib.o"))
timers['execution_time_upload_graph']=time.time()-dt
lib = remote.load_module("graphlib.o")
ctx = remote.ext_dev(0) if "vta" in target else remote.cpu(0)

print("Build complete...")

def run_e2e(graph):
    """Running end to end example
    """
    if debug_fpga_only:
        graph = mark_nop(graph, skip_conv_layer=(0,))
    dt=time.time()
    m = graph_runtime.create(graph, lib, ctx)
    timers['execution_time_create_run_time_graph']=(time.time()-dt)
    # set inputs
    m.set_input('data', tvm.nd.array(x.astype("float32")))
    m.set_input(**params)
    # execute
    print ("run ("+str(STAT_REPEAT)+")")
    dt=time.time()
    timer = m.module.time_evaluator("run", ctx, number=STAT_REPEAT)
    timers['execution_time_classify']=(time.time()-dt)/STAT_REPEAT
    tcost = timer()

    # get outputs
    tvm_output = m.get_output(
        0,tvm.nd.empty((1000,), dtype, remote.cpu(0)))
    top1 = np.argmax(tvm_output.asnumpy())
    print('TVM prediction top-1:', top1, synset[top1])
    print("t-cost=%g" % tcost.mean)

    timers['execution_time_classify_internal']=tcost.mean
    timers['execution_time']=tcost.mean

    import json
    with open ('tmp-ck-timer.json', 'w') as ftimers:
         json.dump(timers, ftimers, indent=2)

def run_layer(old_graph):
    """Run a certain layer."""
    for layer_id in range(1, 2):
        graph = mark_nop(old_graph, layer_id)
        m = graph_runtime.create(graph, lib, ctx)
        # set inputs
        m.set_input('data', tvm.nd.array(x.astype("float32")))
        m.set_input(**params)
        # execute
        timer = m.module.time_evaluator("run", ctx, number=10)
        tcost = timer()
        print("resnet[%d]: %g\n"% (layer_id, tcost.mean))

run_e2e(graph)
