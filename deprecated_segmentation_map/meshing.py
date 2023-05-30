from taskqueue import LocalTaskQueue
import igneous.task_creation as tc
import sys
# Mesh on 8 cores, use True to use all cores
# 
cloudpath = sys.argv[1]
x = sys.argv[2]
y = sys.argv[3]
z = sys.argv[4] 
tq = LocalTaskQueue(parallel=True)
tasks = tc.create_meshing_tasks(cloudpath, mip=0, shape=(x, y, z))
tq.insert(tasks)
tq.execute()
tasks = tc.create_mesh_manifest_tasks(cloudpath)
tq.insert(tasks)
tq.execute()
print("Done meshing!")