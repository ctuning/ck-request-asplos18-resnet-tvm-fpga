#! /usr/bin/python
import ck.kernel as ck
import os

# See accuracy.out in experiment:ck-request-asplos18-tvm-fpga-performance-xilinx-pynq-z1-fpga.resnet18-int8-20180404
accuracy_top1=0.37
accuracy_top5=0.63

def do(i):

    # List performance entries
    r=ck.access({'action':'search',
                 'module_uoa':'experiment',
                 'data_uoa':'ck-request-asplos18-tvm-fpga-performance-*'
#                 'repo_uoa':'ck-request-asplos18-results'
                })
    if r['return']>0: return r
    lst=r['lst']

    for q in lst:
        duid=q['data_uid']
        duoa=q['data_uoa']
        ruid=q['repo_uid']
        path=q['path']

        ck.out(duoa)

        # Search matching accuracy entry
        r=ck.access({'action':'load',
                     'module_uoa':'experiment',
                     'data_uoa':duid,
                     'repo_uoa':ruid})
        if r['return']>0: return r

        dd=r['dict']
        ruid=r['repo_uid']
        apath=r['path']             

        # Updating meta if needed
        dd['meta']['scenario_module_uoa']='a555738be4b65860' # module:request.asplos18

        dd['meta']['model_species']='d41bbf1e489ab5e0' # model.species:resnet18

        dd['meta']['dataset_species']='ImageNet' # dataset species (free format)
        dd['meta']['dataset_size']=2000 # number of images ...

        dd['meta']['platform_species']='fpga' # embedded vs server vs fpga (maybe other classifications such as edge)

        dd['meta']['platform_peak_power']=2.5 #Watts
        dd['meta']['platform_price']=229 # $
        dd['meta']['platform_price_date']='20180404' # date

        dd['meta']['artifact']='9375838469ad4029' # artifact description

        dd['meta']['model_precision']='int8'

        dd['meta']['processed']='yes'

        # Unified full name for some deps
        ds=dd['meta']['deps_summary']

        x=ds['model']
        r=ck.access({'action':'make_deps_full_name','module_uoa':'request.asplos18','deps':x})
        if r['return']>0: return r

        dd['meta']['model_design_name']=r['full_name']
        dd['meta']['plat_name']='Xilinx PYNQ-Z1 FPGA (ZYNQ XC7Z020-1CLG400C)'
        dd['meta']['os_name']='Ubuntu 15.10'
        dd['meta']['cpu_name']='Programmable logic equivalent to Artix-7 FPGA'

        # Updating entry
        r=ck.access({'action':'update',
                     'module_uoa':'experiment',
                     'data_uoa':duid,
                     'repo_uoa':ruid,
                     'dict':dd,
                     'substitute':'yes',
                     'ignore_update':'yes',
                     'sort_keys':'yes'
                    })
        if r['return']>0: return r

        # Checking points to aggregate
        os.chdir(path)
        dperf=os.listdir(path)
        for f in dperf:
            if f.endswith('.cache.json'):
               os.system('git rm -f '+f)

            elif f.endswith('.flat.json'):
               ck.out(' * '+f)

               # Load performance file 
               p1=os.path.join(path, f)

               r=ck.load_json_file({'json_file':p1})
               if r['return']>0: return r
               d1=r['dict']

               # Prune some old value
               d={}
               for k in d1:
                   if not k.startswith('##characteristics#run#accuracy_top1') and \
                      not k.startswith('##characteristics#run#accuracy_top5') and \
                      not k.startswith('##characteristics#run#inference_throughput') and \
                      not k.startswith('##characteristics#run#inference_latency'):
                      d[k]=d1[k]

               d['##features#model_size#min']=129770

               d['##features#gpu_freq#min']=500
               d['##features#cpu_freq#min']=''
               d['##features#freq#min']=d['##features#gpu_freq#min']

               d['##features#processed#min']='yes'

               # Add throughput (images/second)
               tall=d.get('##characteristics#run#execution_time_classify_internal#all',[]) # It's internal VTA measurements
               if len(tall)>0:
                  tnew=[]
                  for t in tall:
                      t1=1/t
                      tnew.append(t1)
                  
                  r=ck.access({'action':'stat_analysis',
                               'module_uoa':'experiment',
                               'dict':d,
                               'dict1':{'##characteristics#run#inference_throughput':tnew}
                              })
                  if r['return']>0: return r

               # Unify batch size
               batch=1 # for now only 1 is supported in this artifact
               d['##features#batch_size#min']=batch

               # inference latency
               d['##features#measuring_latency#min']='yes'

               r=ck.access({'action':'stat_analysis',
                            'module_uoa':'experiment',
                            'dict':d,
                            'dict1':{'##characteristics#run#inference_latency':tall}
                           })
               if r['return']>0: return r

               r=ck.access({'action':'stat_analysis',
                            'module_uoa':'experiment',
                            'dict':d,
                            'dict1':{'##characteristics#run#prediction_time_avg_s':tall}
                           })
               if r['return']>0: return r

               # Add accuracy (was calculated through separate experiment)
               r=ck.access({'action':'stat_analysis',
                            'module_uoa':'experiment',
                            'dict':d,
                            'dict1':{'##characteristics#run#accuracy_top1':[accuracy_top1]}
                           })
               if r['return']>0: return r

               # Add accuracy (was calculated through separate experiment)
               r=ck.access({'action':'stat_analysis',
                            'module_uoa':'experiment',
                            'dict':d,
                            'dict1':{'##characteristics#run#accuracy_top5':[accuracy_top5]}
                           })
               if r['return']>0: return r

               # Save updated dict
               r=ck.save_json_to_file({'json_file':p1, 'dict':d, 'sort_keys':'yes'})
               if r['return']>0: return r

    return {'return':0}

r=do({})
if r['return']>0: ck.err(r)
