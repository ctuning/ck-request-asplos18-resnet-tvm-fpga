#! /usr/bin/python
import ck.kernel as ck
import copy
import re
import argparse


# ReQuEST description.
request_dict={
  'report_uid':'9375838469ad4029', # unique UID for a given ReQuEST submission generated manually by user (ck uid)
                                   # the same UID will be for the "report" and "artifact" (in the same repo)

  'repo_uoa':'ck-request-asplos18-resnet-tvm-fpga',
  'repo_uid':'3344889dba78837b',

  'repo_cmd':'ck pull repo:ck-request-asplos18-resnet-tvm-fpga',

  'farm':'', # if farm of machines

  'algorithm_species':'4b8bbc192ec57f63' # image classification
}

# Platform tags.
platform_tags='xilinx-pynq-z1-fpga'
target='pynq' # should be added/configured as RPC access via "ck add machine:pynq" before experiments

# Number of statistical repetitions.
num_repetitions=3 # however there is already an internal stat. repetition ...

def do(i, arg):

    random_name = arg.random_name

    # Detect basic platform info.
    ii={'action':'detect',
        'module_uoa':'platform',
        'target':target,
        'out':'out'}
    r=ck.access(ii)
    if r['return']>0: return r

    # Keep to prepare ReQuEST meta.
    platform_dict=copy.deepcopy(r)

    # Host and target OS params.
    hos=r['host_os_uoa']
    hosd=r['host_os_dict']

    tos=r['os_uoa']
    tosd=r['os_dict']
    tdid=r['device_id']

    # Program and command.
    program='request-tvm-vta-pynq'
    cmd_key='classify'
    dset='e496fdf046e6ac13' # image-jpeg-dnn-cat

    # Load program meta and desc to check deps.
    ii={'action':'load',
        'module_uoa':'program',
        'data_uoa':program}
    rx=ck.access(ii)
    if rx['return']>0: return rx
    mm=rx['dict']

    # Get deps
    deps=mm.get('run_cmds',{}).get('classify',{}).get('run_deps',{})

    # Models
    depm=copy.deepcopy(deps['model'])

    ii={'action':'resolve',
        'module_uoa':'env',
        'host_os':hos,
        'target_os':tos,
        'device_id':tdid,
        'out':'con',
        'quiet':'yes',
        'deps':{'model':copy.deepcopy(depm)}
    }
    r=ck.access(ii)
    if r['return']>0: return r

    udepm=r['deps']['model'].get('choices',[]) # All UOAs of env for Caffe models.
    if len(udepm)==0:
        return {'return':1, 'error':'no installed VTA models'}

    deps['model']['uoa']=udepm[0]

    ii={'action':'pipeline',
        'prepare':'yes',
        'dependencies':deps,

        'module_uoa':'program',
        'data_uoa':program,
        'cmd_key':cmd_key,
        'dataset_uoa':dset,

        'target':target,
        'target_os':tos,
        'device_id':tdid,

        'no_state_check':'yes',
        'no_compiler_description':'yes',
        'skip_calibration':'yes',

#       not needed since it's not running on host ...
#       'cpu_freq':'max',
#       'gpu_freq':'max',

        'flags':'-O3',
        'speed':'no',
        'energy':'no',

        'skip_print_timers':'yes',
        'out':'con'
    }

    r=ck.access(ii)
    if r['return']>0: return r

    fail=r.get('fail','')
    if fail=='yes':
        return {'return':10, 'error':'pipeline failed ('+r.get('fail_reason','')+')'}

    ready=r.get('ready','')
    if ready!='yes':
        return {'return':11, 'error':'pipeline not ready'}

    state=r['state']
    tmp_dir=state['tmp_dir']

    # Remember resolved deps for this benchmarking session.
    xdeps=r.get('dependencies',{})

    # Clean pipeline.
    if 'ready' in r: del(r['ready'])
    if 'fail' in r: del(r['fail'])
    if 'return' in r: del(r['return'])

    pipeline=copy.deepcopy(r)

    for dummy in ['dummy']:
        # For each model.*************************************************
        for model_uoa in udepm:
            # Load model.
            ii={'action':'load',
                'module_uoa':'env',
                'data_uoa':model_uoa}
            r=ck.access(ii)
            if r['return']>0: return r

            model_real_tags=r['dict']['tags']

            # Get the tags from e.g. 'Caffe model (net and weights) (inception-v3, fp32)'
            model_name=r['data_name']
            model_tags = re.match('VTA model \(net and weights\) \((?P<tags>.*)\)', model_name)
            model_tags = model_tags.group('tags').replace(' ', '').replace(',', '-')

            # Get extra tags 
            model_name=r['data_name']

            record_repo='local'
            record_uoa='ck-request-asplos18-tvm-fpga-performance-'+platform_tags+'.'+model_tags

            # Prepare pipeline.
            ck.out('---------------------------------------------------------------------------------------')
            ck.out('%s - %s' % (model_name, model_uoa))
            ck.out('Experiment - %s:%s' % (record_repo, record_uoa))

            # Prepare autotuning input.
            cpipeline=copy.deepcopy(pipeline)

            # Reset deps and change UOA.
            new_deps={'model':copy.deepcopy(depm)}

            new_deps['model']['uoa']=model_uoa

            jj={'action':'resolve',
                'module_uoa':'env',
                'host_os':hos,
                'target_os':tos,
                'device_id':tdid,
                'deps':new_deps}
            r=ck.access(jj)
            if r['return']>0: return r

            cpipeline['dependencies'].update(new_deps)

            cpipeline['cmd_key']=cmd_key

            # Prepare common meta for ReQuEST tournament
            features=copy.deepcopy(cpipeline['features'])
            platform_dict['features'].update(features)

            r=ck.access({'action':'prepare_common_meta',
                         'module_uoa':'request.asplos18',
                         'platform_dict':platform_dict,
                         'deps':cpipeline['dependencies'],
                         'request_dict':request_dict})
            if r['return']>0: return r

            record_dict=r['record_dict']

            meta=r['meta']

            if random_name:
               rx=ck.gen_uid({})
               if rx['return']>0: return rx
               record_uoa=rx['data_uid']

            tags=r['tags']

            tags.append(program)
            tags.append(model_tags)
            tags.append(platform_tags)

            ii={'action':'autotune',

                'target':target,

                'module_uoa':'pipeline',
                'data_uoa':'program',

                'iterations':1,
                'repetitions':num_repetitions,

                'record':'yes',
                'record_failed':'yes',
                'record_params':{
                    'search_point_by_features':'yes'
                },

                'tags':tags,
                'meta':meta,

                'record_dict':record_dict,

                'record_repo':record_repo,
                'record_uoa':record_uoa,

                'pipeline':cpipeline,
                'out':'con'}

            r=ck.access(ii)
            if r['return']>0: return r

            fail=r.get('fail','')
            if fail=='yes':
                return {'return':10, 'error':'pipeline failed ('+r.get('fail_reason','')+')'}

            skip_compile='yes'

    return {'return':0}

##############################################################################################

parser = argparse.ArgumentParser(description='Pipeline')
parser.add_argument("--target_os", action="store", dest="tos")
parser.add_argument("--device_id", action="store", dest="did")
parser.add_argument("--random_name", action="store_true", default=False, dest="random_name")
myarg=parser.parse_args()

r=do({}, myarg)
if r['return']>0: ck.err(r)
