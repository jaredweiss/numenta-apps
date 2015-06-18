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
[Documentation](https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/kubectl.md)
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
