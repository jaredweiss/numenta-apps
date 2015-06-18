Install dependencies
--------------------

* [VirtualBox](https://www.virtualbox.org/wiki/Downloads) 4.3.10 or greater.
* [Vagrant](http://www.vagrantup.com/downloads.html) 1.6 or greater.
* Docker Client that supports the `-f` arg (https://docs.docker.com/installation/mac/)

Startup
-------

From within the `infrastructure/kubernetes/` directory:

```
vagrant up
source env
```

``vagrant up`` triggers vagrant to download the CoreOS image (if necessary) and (re)launch the instance

CoreOS starts up with the following units:

- Docker (and a tcp socket)

- Flannel (for managing the vIPs kubernetes uses on pods)

- [**kube-apiserver**](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/man/kube-apiserver.1.md):
  controls kubernetes; interacts with kubectl on a client

  **Note:** only one of these will run on a proper kubernetes cluster, while
  the following kube-* processes will run on every *node*. All of the other processes link to the api (in [user-data](user-data) apears as the flag ```--master=127.0.0.1:8080```)

- [**kube-controller-manager**](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/man/kube-controller-manager.1.md):
  a service for running [replication-controllers](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/replication-controller.md) on a node

- [**kube-scheduler**](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/man/kube-scheduler.1.md):
  manages the node's resources within kubernetes

- [**kube-proxy**](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/man/kube-proxy.1.md):
  Handles using [services](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/services.md) on a node

- [**kubelet**](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/man/kubelet.1.md):
  Handles running [pods](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/pods.md) on a node



Kubernetes + a Docker Registry
------------------------------
Kuberenetes treats images a bit differently than docker does [*see here...*](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/images.md). Basically, Kubernetes doesn't pull images built using the local docker image cache. Instead, it gets images from docker registries (note: this DOES include the localhost:5000 registry if you want to build/push to a registry running on the same node as Kubernetes). For the sake of simplicity, here we describe using a private docker registry denoted throughout this readme as ```<registry>```. Simply replace this with any private or public registry. Just be certain the registry DOESN'T require any authentication and the ```--insecure-registry``` option is set when launching the docker daemon. 

Before running any of these examples, you'll need to replace ```<registry>``` with
an actual url. Here's a list of files to update:
- taurus/support.yaml (line 14)
- taurus/taurus-server.yaml (line 13)
- user-data (line 8)

We use the DOCKER_OPTS envvar to tell the docker daemon our server is insecure. This is set in our [user-data](user-data) file with the following lines: 
'''
write_files:
- path: /etc/systemd/system/docker.service.d/50-insecure-registry.conf
  content: |
    [Service]
    Environment='DOCKER_OPTS=--insecure-registry="<registry>"'
'''


Building Taurus for Kubernetes
------------------------------
These steps are based off of building Taurus for [CoreOS running on Vagrant](../coreos/) 

In the root ```numenta-apps``` directory

NOTE: If you're doing any kind of local development, remember to run
```$ find . -name "*.pyc" -exec rm -rf {} \;```
to remove any cached python files.


```
docker build -t <registry>/nta.utils:latest nta.utils
docker build -t <registry>/htmengine:latest htmengine
docker build -t <registry>/taurus.metric_collectors:latest taurus.metric_collectors
docker build -t <registry>/taurus:latest taurus
docker build -t <registry>/taurus-dynamodb:latest taurus/external/dynamodb_test_tool

docker push <registry>/nta.utils:latest
docker push <registry>/htmengine:latest
docker push <registry>/taurus.metric_collectors:latest
docker push <registry>/taurus:latest
docker push <registry>/taurus-dynamodb:latest
```

Pulling (pre-built) Taurus images
---------------------------------
If you've already built the images and pushed them to your registry, there's
no need to rebuild them unless you've made changes to their code. To simply fetch
them from the registry so they're on your machine run the folowing:

```
docker pull <registry>/nta.utils:latest
docker pull <registry>/htmengine:latest
docker pull <registry>/taurus.metric_collectors:latest
docker pull <registry>/taurus:latest
docker pull <registry>/taurus-dynamodb:latest
```

Running Taurus on Kubernetes
----------------------------

Get ```kubectl```:
[Download](https://storage.googleapis.com/kubernetes-release/release/v0.17.0/bin/darwin/amd64/kubectl)
[(documentation)](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/kubectl.md)
```
chmod +x ~/Downloads/kubectl
mv ~/Downloads/kubectl /usr/local/bin
```

Try it out: 
```kubectl get nodes```
should return 
```
NAME        LABELS                             STATUS
127.0.0.1   kubernetes.io/hostname=127.0.0.1   Ready
```
If it doesn't, make sure that vagrant has finished downloading and running all of the kube-* processes in [user-data](user-data).


Start the support pods and services ([support.yaml](taurus/support.yaml)):
```kubectl create -f taurus/support.yaml```

Check that all the pods are in *RUNNING* state before starting the server by running: 
```kubectl get pods```

Then run the taurus server ([taurus-server.yaml](taurus/taurus-server.yaml)): 
```kubectl create -f taurus/taurus-server.yaml```

Inspecting logs: 
```kubectl log taurus-server taurus```

Other Kubernetes Use Cases
--------------------------

- **How do you run a cron job in the cloud?**
  *not implemented yet in kubernetes...* [issue](https://github.com/GoogleCloudPlatform/kubernetes/issues/503#issuecomment-50169443)

  (Temporary solution) Put this in crontab:
  ```0 0 * * * /bin/kubectl create -f <some one-off pod> ```

  Or make a fleet unit with a [Timer]... ([example here](http://blog.maxcnunes.net/2015/02/01/coreos-scheduled-tasks/))

- **How do you run a "batch job" (like a research experiment)?**
  Ex: *[batch-job.yaml](examples/batch-job/batch-job.yaml)*
  ```kubectl create -f examples/batch-job/batch-job.yaml```
  ```
  apiVersion: v1beta3
  kind: Pod
  metadata:
    name: batch-job
    labels: 
      name: batch-job
  spec: 
    containers: 
      - name: nupic-region-test
        image: numenta/nupic:latest
        command: 
          - /bin/bash
          - -c
          - /usr/local/src/nupic/bin/py_region_test
    restartPolicy: Never
  ```

  Run ```kubectl get status```:
  ```
  POD             IP            CONTAINER(S)    IMAGE(S)                                                            HOST                  LABELS                                 STATUS       CREATED         MESSAGE
  batch-job                                                                                                          127.0.0.1/127.0.0.1   name=batch-job                          Succeeded    52 seconds
                                nupic-region-test        numenta/nupic:latest                                                                                                             Terminated   27 seconds      exit code 0
  ```

  Once the pod has Terminated, running ```kubectl log batch-job nupic-region-test``` will show the output of the test.

  **Note:** to stream logs run ```kubectl log -f <pod> <container>```. Useful for long-running tests

- **How do I run a batch job that is parallelized across X machines?**
  One use case (using RMQ, a mater node, and worker nodes). The master + workers
  are task specific.

    - Start RMQ node: ```kubectl create -f examples/parallelizing/rabbit.yaml```
    - Start a worker replicator: ```kubectl create -f examples/parallelizing/worker-replicator.yaml```
    - Start a master node: ```kubectl create -f examples/parallelizing/master.yaml```

  View the log of the master node with ```kubectl log master master -f```

- **How do you run a long-running service?**
  Look at the taurus example

- **How do I put static files up that I can share our link to elsewhere?** 
  Use a kubernetes service to point to a pod. Look at how it's done in the
  taurus example. Also take note how storage is kept consistant in these situations.

  A replication controller wraping a pod would also be beneficial in this situation
  to ensure there was always a pod running.

- **How do you assign DNS entries to a long-running service?**
  [Just declare the service with a specific IP](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/services.md#choosing-your-own-ip-address)

  Services implement a primative load-balancing that binds the service to 
  an external IP. This IP stays constant even if kubernetes assigns the pod to
  another node. 

  This command would get the external IP of a service called 'example-frontend' runnign with a load balancer:
  ```$ kubectl get services/example-frontend --template="{{range .status.loadBalancer.ingress}} {{.ip}} {{end}}"```

- **Can I run applications without an internet connection?**
  You will need to set up a local docker registry on one of the nodes. Any images
  built will need to use the IP for that machine as the registry name...
  ```docker build -t 10.0.2.15/example-image .```
  ```docker push 10.0.2.15/example-image```

- **Can I run a CI build job on my laptop without an internet connection?**
  Yes. You'll still need a local registry running on your Vagrant machine
  (see [user-data-local-registry](user-data-local-registry))

- **How do we configure users?**
  Nothing right now...

- **How do we track user actions a) updating infrastructure / terraform commands and b) launching applications / fleet commands?** 
  See above?

- **Are there any steps blocked by a person other than the engineer doing something? Like infra starting a server, etc.**

- **How do we create a machine image preconfigured for one of our applications (like Grok for AWS Marketplace)?**
  Build the image and push it to a registry. Then anyone with the registry link
  ([and optionally credentials](https://docs.docker.com/reference/commandline/cli/#login:b659b046131d4024ab5e2d3675716bf0)) can pull.

- **How do you launch a cluster?**
  (out of scope)
  
- **How do we see which clusters are running?**
  (out of scope)

- **How do we see what is running on a cluster?**
  fleetctl, kubectl, tooling
  kubernetes has a nice [api](kubernetes.io/third_party/swagger-ui/) if we want
  to write a nice interface

- **How do you scale a cluster?**

- **How do engineers run and manage docker containers locally? Boot2docker? Kitematic? We should have a recommendation**
  See the examples I've included here. All are designed to run locally. 

- **How do you debug code inside a container? View logs, set breakpoint, etc.**
  ```kubectl log <pod> <container>```

