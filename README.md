[![logo](https://github.com/ctuning/ck-guide-images/blob/master/logo-powered-by-ck.png)](https://github.com/ctuning/ck)

This repository contains experimental workflow and all related artifacts 
as portable, customizable and reusable [Collective Knowledge components](https://github.com/ctuning/ck)
for image classification from the [1st ReQuEST tournament at ASPLOS'18](http://cknowledge.org/request-cfp-asplos2018.html) 
on reproducible SW/HW co-design of deep learning (speed, accuracy, energy, costs).

## References

* **Title:** VTA: Open Hardware/Software Stack for Vertical Deep Learning System Optimization
* **Authors:** Thierry Moreau, Tianqi Chen, Luis Ceze

* [ACM paper](https://doi.org/10.1145/3229762.3229766)
* [ACM artifact](https://doi.org/10.1145/3229772)

* [arXiv ReQuEST goals](https://arxiv.org/abs/1801.06378)

## Artifact check-list (meta-information)

We use the standard [Artifact Description check-list](http://ctuning.org/ae/submission_extra.html) from systems conferences including CGO, PPoPP, PACT and SuperComputing.

* **Algorithm:** image classification
* **Program:** image classification and accuracy validation
* **Compilation:** GCC and LLVM >=4
* **Transformations:** TVM
* **Binary:** will be compiled on a target platform
* **Data set:** ImageNet 2012 validation (50,000 images) and ResNet-18 8-bit
* **Run-time environment:** Ubuntu 15.04
* **Hardware:** Xilinx Pynq-Z1 FPGA
* **Run-time state:** 
* **Execution:** remote execution via RPC
* **Metrics:** total execution time; top1/top5 accuracy over some (all) images from the data set
* **Output:** classification result; execution time; accuracy
* **Experiments:** CK command line
* **How much disk space required (approximately)?** 
* **How much time is needed to prepare workflow (approximately)?** 30 minutes
* **How much time is needed to complete experiments (approximately)?** 1 minute to test classification and .. hours to test accuracy
* **Collective Knowledge workflow framework used?** Yes
* **Publicly available?:** Yes
* **Experimental results:** https://github.com/ctuning/ck-request-asplos18-results-resnet-tvm-fpga
* **Scoreboard:** http://cKnowledge.org/request-results

## Installation: PYNQ-Z1 FPGA (connected via RPC from host)

Please follow this [getting started guide]() to set up your Pynq board.

We used pynq_z1_image_2017_02_10.img with 16GB microSD card and Ubuntu 15.04.

Turn on your board. You should now be able to connect to it as follows:

```
$ ssh xilinx@192.168.2.99
```

Use 'xilinx' as password.

### Install global prerequisites (Ubuntu)

Note that Ubuntu 15.04 is now outdated. You need to fix URLs of Ubuntu repos to be able to update it and install missing packages as follows:

```
$ sudo vim /etc/apt/sources.list.d/multistrap-wily.list
 deb [arch=armhf] http://old-releases.ubuntu.com/ubuntu wily universe main
 deb-src http://old-releases.ubuntu.com/ubuntu wily universe main
```

Then you should be able to upgrade your distribution as follows:
```
$ sudo apt update
$ sudo apt upgrade
```

Now you can install missing deps:
```
$ sudo apt install python-pip python3-pip
$ pip install wget

```

### Install Collective Knowledge and this repository with all deps
```
$ sudo pip install ck
$ ck pull repo:ck-request-asplos18-resnet-tvm-fpga
```

### Install and run VTA RPC server via CK

```
$ ck install package:lib-tvm-runtime-master --env.PACKAGE_GIT_CHECKOUT=e4c2af9abdcb3c7aabafba8084414d7739c17c4c

  choose Python 3!

$ ck run program:vta-pynq-server --sudo

  during first execution other missing soft dependencies will be detected or installed including libdma.so and VTA server

```

Note that by default this server will run on host '192.168.2.99' and port '9091'.

Now you can configure your host machine to classify images via this board.


## Installation: host machine (tested on Ubuntu or similar)

Install missing deps:
```
$ sudo apt install python-pip python3-pip
$ pip install wget

```

### Install Collective Knowledge and this repository with all deps
```
$ sudo pip install ck
$ ck pull repo:ck-request-asplos18-resnet-tvm-fpga
```

### Install TVM, NNVM and VTA

```
$ ck install package:lib-tvm-master-cpu --env.PACKAGE_GIT_CHECKOUT=e4c2af9abdcb3c7aabafba8084414d7739c17c4c
 Select Python 2.x
 LLVM > 4.x

$ ck install package:lib-nnvm-master --env.PACKAGE_URL=https://github.com/tqchen/nnvm --env.PACKAGE_GIT_CHECKOUT=qt

$ ck install package:lib-vta-python-master
```

### Set up RPC access to VTA server
```
$ ck add machine:pynq
```

Select "remote machine accessed via RPC", then enter hostname and port.

You can then check if VTA server running as follows:
```
$ ck show machine
```

### Run classification
You can now try to classify some image via VTA server as follows:
```
$ ck run program:request-tvm-vta-pynq --cmd_key=classify --target=pynq
```

### Test accuracy
Finally, you can test accuracy on IMAGENET as follows:
```
$ ck run program:request-tvm-vta-pynq --cmd_key=test target=pynq
```

Note that if board crahes, you can restart above program and it will continue aggregating statistics
via program/request-tvm-vta-pynq/tmp/aggregate-ck-timer.json file. You can delete it if you want to collect "fresh" stats.

### Run benchmarking in a unified ReQuEST way and record results

You can run performance benchmark and record experiments as follows:
```
$ cd `ck find script:benchmark-request-tvm-fpga`
$ python benchmarking.py
```

Your results will be recorded in local:experiment:ck-request-asplos18-tvm-fpga-performance-* entries:
```
$ ck ls local:experiment:ck-request-asplos18-tvm-fpga-performance-*
```

## Reviewers

This workflow was converted to CK and validated by the following reviewers:
* [Grigori Fursin](http://fursin.net/research.html)
