# AKS / Production Notes

This document contains quick steps and notes for running SonarSniffer in AKS.

1) Ingress + TLS
- Install an ingress controller (NGINX or AGIC).
- Install cert-manager and create a ClusterIssuer (or set `values.certManager.createClusterIssuer=true` and apply a ClusterIssuer manually).
- Values to configure in `helm/sonarsniffer/values.yaml`: `ingress.host`, `ingress.tls.secretName`, `certManager.issuer`.

2) Secrets
- For production secrets we recommend using Azure Key Vault with Secrets Store CSI or Workload Identity.
- The chart contains a `SecretProviderClass` template which is applied when `keyVault.enabled=true`.

3) Autoscaling
- The chart enables an HPA (based on CPU) and optionally adds a KEDA `ScaledObject` when `keda.enabled=true`.
- Configure `keda.redis.address` with your Redis connection string and `keda.redis.listName` for the queue.

4) CI/CD
- A GitHub Actions workflow `/.github/workflows/ci-deploy.yml` is included as a starter. It requires:
  - `AZURE_CREDENTIALS` (service principal JSON)
  - `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`

5) Helm deploy (local)
- Install Helm then:
  helm upgrade --install sonarsniffer ./helm/sonarsniffer -n sonarsniffer --create-namespace --set image.tag=<tag>

6) Next steps
- Install cert-manager and configure a ClusterIssuer.
- Decide on Key Vault approach (CSI vs Workload Identity). Workload Identity requires enabling OIDC for the cluster.

Quick install commands (what I ran):
- kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml
- kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
- kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.10.0/keda-2.10.0.yaml
- kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml
- Create a self-signed ClusterIssuer for quick TLS tests: see `k8s/cert-manager-clusterissuer.yaml`

Quick tests I ran to validate stack:
1. Confirmed ingress LB and created an ingress for `sonarsniffer.<LB_IP>.nip.io` and verified TLS via self-signed ClusterIssuer (certificate ready). ✅
2. Deployed a small Redis instance (`k8s/redis.yaml`) and created a `ScaledObject` (`k8s/keda-scaledobject.yaml`) to scale the app based on Redis list length. Pushed test items into Redis and saw the Deployment scale from 1 → 2. ✅
3. Confirmed the application UI is accessible at the test domain (self-signed TLS) and that KEDA created an HPA and scaled the deployment when items were queued. ✅

Notes:
- Key Vault integration is scaffolded via `helm/sonarsniffer/templates/secretproviderclass.yaml`. It requires identity (Workload Identity or Managed Identity) and Key Vault access to work in production.
- The CI workflow (.github/workflows/ci-deploy.yml) is a starter; add GitHub secrets for ACR and Azure service principal to enable automatic build-and-deploy.
