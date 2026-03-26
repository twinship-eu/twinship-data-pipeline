# TwinShip Pipeline Profiling with SIM-PIPE

This directory contains an Argo Workflow that runs each Dagster pipeline step as a separate container, enabling per-step CPU/memory profiling via SIM-PIPE.

## Prerequisites

- **Git** and **kubectl** (all platforms)
- **Helm 3** — [install instructions](https://helm.sh/docs/intro/install/)
- **Argo CLI** (optional) — [install instructions](https://argo-workflows.readthedocs.io/en/latest/walk-through/argo-cli/)
- **Docker** and a **local Kubernetes cluster** — see platform-specific setup below

### macOS

```bash
brew install colima helm kubectl argo
```

### Windows

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and enable **Kubernetes** in Settings > Kubernetes
2. Install Helm: `winget install Helm.Helm`
3. Install kubectl: `winget install Kubernetes.kubectl`

### Linux

```bash
# Docker
curl -fsSL https://get.docker.com | sh

# Colima (recommended for local k8s)
curl -LO https://github.com/abiosoft/colima/releases/latest/download/colima-Linux-x86_64
sudo install colima-Linux-x86_64 /usr/local/bin/colima

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

## 1. Start a local Kubernetes cluster

### macOS / Linux (Colima)

```bash
colima start -p simpipe \
  --runtime docker \
  --kubernetes \
  --kubernetes-version v1.28.3+k3s2 \
  --cpu 4 --memory 8
```

The first boot may take a few minutes while it downloads the VM image and bootstraps k3s.

Verify:

```bash
kubectl --context colima-simpipe get nodes
```

### Windows (Docker Desktop)

Enable Kubernetes in Docker Desktop settings and wait for it to be ready. The kubectl context will be `docker-desktop`.

Verify:

```bash
kubectl --context docker-desktop get nodes
```

> In all subsequent commands, replace `colima-simpipe` with `docker-desktop` if using Docker Desktop.

## 2. Install SIM-PIPE

Clone the SIM-PIPE repository:

```bash
git clone https://github.com/DataCloud-project/SIM-PIPE.git
cd SIM-PIPE
```

Install the Helm chart:

```bash
helm install simpipe ./charts/simpipe \
  --kube-context colima-simpipe \
  --set cadvisor.image.repository="ghcr.io/google/cadvisor" \
  --set cadvisor.image.tag="0.55.1" \
  --set postgresql.image.repository="bitnamilegacy/postgresql" \
  --set minio.image.repository="bitnamilegacy/minio" \
  --set minio.clientImage.repository="bitnamilegacy/minio-client"
```

> **Note on image overrides:**
> - **cAdvisor**: Docker 28+ uses containerd-snapshotters which breaks cAdvisor < 0.54.0.
>   The overrides above switch to `ghcr.io/google/cadvisor:0.55.1` which supports it.
>   If your Docker version is 27 or earlier, you can omit the cadvisor overrides.
> - **Bitnami images**: The SIM-PIPE chart references old Bitnami image tags that have
>   been removed from Docker Hub. The `bitnamilegacy/` repositories still host them.

Wait for all pods to be ready:

```bash
kubectl --context colima-simpipe get pods -w
```

## 3. Set up port forwarding

From the SIM-PIPE repository:

```bash
python forwarding.py
```

This forwards the following services to localhost:

| Service | URL |
|---|---|
| Argo Workflows UI | http://localhost:8084 |
| SIM-PIPE Frontend | http://localhost:8088 |
| MinIO | http://localhost:8085 |

## 4. Create the TwinShip project in SIM-PIPE

Open http://localhost:8088, go to **Projects**, and create a new project named `twinship`.

Alternatively, via the GraphQL API:

```bash
curl -s http://localhost:8087/graphql -H "Content-Type: application/json" -d "{\"query\": \"mutation { createProject(project: { name: \\\"twinship\\\", id: \\\"twinship\\\" }) { id name } }\"}"
```

## 5. Build and load the Docker image

From the `twinship-data-pipeline` repository root:

### macOS / Linux (Colima)

```bash
# Build the image
docker --context colima-simpipe build -t twinship_user_code:latest -f Dockerfile .

# Load into k3s
docker --context colima-simpipe save twinship_user_code:latest -o /tmp/twinship_user_code.tar
colima ssh -p simpipe -- sudo ctr --namespace k8s.io images import - < /tmp/twinship_user_code.tar
```

### Windows (Docker Desktop)

```bash
docker build -t twinship_user_code:latest -f Dockerfile .
```

Docker Desktop shares its image store with Kubernetes, so no extra loading step is needed.

## 6. Submit the workflow

```bash
kubectl --context colima-simpipe create -f argo/twinship-profiling.yaml
```

Monitor progress:

```bash
# Via kubectl
kubectl --context colima-simpipe get pods -w

# Or via Argo CLI
argo --context colima-simpipe list
argo --context colima-simpipe watch @latest
```

## 7. View profiling results

- **Argo UI** (http://localhost:8084): Shows the DAG, per-step logs, and durations
- **SIM-PIPE Frontend** (http://localhost:8088): Shows per-container CPU/memory/network metrics under the `twinship` project

## How it works

The workflow runs 11 steps as a DAG:

```
extract-spreadsheet
    ├── extract-grimaldi-roro ── harmonise-grimaldi-roro ── validate-grimaldi-roro ──┐
    ├── extract-stena-ropax ── harmonise-... ── validate-... ──┼── combine-graphs
    └── extract-stena-tanker ── harmonise-... ── validate-... ───────┘
```

Each step runs `runner.py` with different arguments inside the `twinship_user_code` Docker image. The runner calls Dagster's `materialize()` API with a custom `SharedVolumeIOManager` that persists asset outputs as pickle files on a shared PVC (`/tmp/pipeline/`), enabling data to pass between containers while profiling the full Dagster execution framework.
