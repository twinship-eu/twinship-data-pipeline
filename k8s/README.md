# Kubernetes Deployment (minikube)

Local Kubernetes deployment using minikube and the Dagster Helm chart. The same `values.yaml` can be adapted for a real cluster.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [minikube](https://minikube.sigs.k8s.io/docs/start/)
- [Helm](https://helm.sh/docs/intro/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

```bash
# macOS
brew install minikube helm kubectl
```

## Initial Setup

```bash
# 1. Start minikube
minikube start --memory=4096 --cpus=2

# 2. Build images
docker build -t twinship_user_code:latest -f Dockerfile .
docker build -t twinship_dagster:latest -f Dockerfile.dagster .

# 3. Load images into minikube
minikube image load twinship_user_code:latest
minikube image load twinship_dagster:latest

# 4. Add Dagster Helm repo
helm repo add dagster https://dagster-io.github.io/helm
helm repo update

# 5. Create namespace and persistent volumes
kubectl create namespace dagster
kubectl apply -f k8s/pipeline-output-pvc.yaml
kubectl apply -f k8s/dagster-storage-pvc.yaml

# 6. Install Dagster
helm upgrade --install dagster dagster/dagster -n dagster -f k8s/values.yaml

# 7. Wait for pods to be ready (~30-60 seconds)
kubectl get pods -n dagster -w

# 8. Access the UI
kubectl port-forward -n dagster svc/dagster-dagster-webserver 3001:80
```

Open http://localhost:3001. The sensor starts automatically, materialises the spreadsheet, discovers vessels, and runs the full pipeline for each.

## Day-to-day Commands

### Start / Stop

```bash
# Start minikube (preserves all state)
minikube start

# Stop minikube (preserves all state)
minikube stop

# Access the UI (runs in foreground, Ctrl+C to stop)
kubectl port-forward -n dagster svc/dagster-dagster-webserver 3001:80
```

### Monitoring

```bash
# Pod status
kubectl get pods -n dagster

# Run jobs
kubectl get jobs -n dagster

# Daemon logs (sensor activity, run queue)
kubectl logs -n dagster deploy/dagster-daemon --tail=50

# Webserver logs
kubectl logs -n dagster deploy/dagster-dagster-webserver --tail=50

# Specific run pod logs
kubectl logs -n dagster <pod-name>

# Check output files
kubectl exec -n dagster deploy/dagster-dagster-user-deployments-twinship-pipeline -- ls -la /app/output/
```

### Rebuilding After Code Changes

```bash
# Rebuild images
docker build -t twinship_user_code:latest -f Dockerfile .
docker build -t twinship_dagster:latest -f Dockerfile.dagster .

# Load into minikube
minikube image load twinship_user_code:latest
minikube image load twinship_dagster:latest

# Restart pods to pick up new images
kubectl rollout restart deploy -n dagster
```

### Updating Helm Configuration

```bash
# After editing k8s/values.yaml
helm upgrade dagster dagster/dagster -n dagster -f k8s/values.yaml
```

### Full Reset (wipe all state)

```bash
helm uninstall dagster -n dagster
kubectl delete pvc --all -n dagster
kubectl delete jobs --all -n dagster

# Recreate
kubectl apply -f k8s/pipeline-output-pvc.yaml
kubectl apply -f k8s/dagster-storage-pvc.yaml
helm upgrade --install dagster dagster/dagster -n dagster -f k8s/values.yaml
```

## Switching Back to Docker Compose

The K8s setup is purely additive — Docker Compose is unchanged.

```bash
minikube stop
docker compose up -d --build
# UI at http://localhost:3000
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ImagePullBackOff` | Check `minikube image ls \| grep twinship` — images must be loaded into minikube |
| Pod crash loops | `kubectl logs -n dagster <pod-name>` |
| Sensor not triggering | `kubectl logs -n dagster deploy/dagster-daemon --tail=50` |
| Run pods fail | `kubectl describe job <job-name> -n dagster` |
| Port 3001 in use | Use a different port: `kubectl port-forward ... 3002:80` |

## Architecture

The Helm chart deploys:

- **PostgreSQL** — Dagster metadata (runs, events, schedules)
- **Webserver** — Dagster UI
- **Daemon** — Sensor polling, run queue coordinator
- **User code deployment** — gRPC server hosting pipeline definitions
- **K8sRunLauncher** — Each pipeline run becomes a Kubernetes Job (ephemeral pod)

Shared storage:
- `dagster-storage` PVC — Dagster IO manager intermediate data (`/opt/dagster/dagster_home/storage`)
- `pipeline-output` PVC — TTL output files (`/app/output`)
