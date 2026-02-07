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
