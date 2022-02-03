# hotstuff

## dependencies:
mpi4py: https://mpi4py.readthedocs.io/en/stable/

to install via pip: 
```
pip3 install mpi4py
```

## command to run:
in general:
```
mpiexec -n [NUMBER_OF_PROCESSES] python thiswasfun.py
```
not enough juice?
```
mpiexec -n [NUMBER_OF_PROCESSES] --use-hwthread-cpus python thiswasfun.py
```
still not enough juice??
```
mpiexec -n [NUMBER_OF_PROCESSES] --use-hwthread-cpus --oversubscribe python thiswasfun.py
```

## things to keep in mind:
* I'm not good at programming
* Python is slow

therefore, the largest region that ran on my laptop was 320x480... more efficient code written in C should scale better
