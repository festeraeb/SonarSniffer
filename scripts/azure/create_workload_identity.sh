#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <app-name> <tenant-id> <rg> <aks-cluster-name> <keyvault-name>"
  exit 2
fi

APP_NAME=$1
TENANT_ID=$2
RG=$3
AKS_CLUSTER=$4
KV_NAME=$5

# Create app registration
APP=$(az ad app create --display-name "$APP_NAME" -o json)
APP_ID=$(echo "$APP" | jq -r .appId)
APP_OBJ_ID=$(echo "$APP" | jq -r .id)

echo "Created app: appId=$APP_ID objectId=$APP_OBJ_ID"

# get AKS issuer URL
ISSUER=$(az aks show -g "$RG" -n "$AKS_CLUSTER" --query "oidcIssuerProfile.issuerUrl" -o tsv)

if [ -z "$ISSUER" ]; then
  echo "OIDC issuer URL not found for cluster $AKS_CLUSTER in $RG"
  exit 3
fi

echo "Using issuer: $ISSUER"

# Replace these values for your service account
NAMESPACE=sonarsniffer
SA_NAME=sonarsniffer-sa

az ad app federated-credential create \
  --id "$APP_ID" \
  --name "${APP_NAME}-federated" \
  --issuer "$ISSUER" \
  --subject "system:serviceaccount:${NAMESPACE}:${SA_NAME}" \
  --audiences "api://AzureADTokenExchange"

# Assign Key Vault Secrets User role at the vault scope
SUB_ID=$(az account show --query id -o tsv)
KV_SCOPE="/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.KeyVault/vaults/${KV_NAME}"

az role assignment create --role "Key Vault Secrets User" --assignee "$APP_OBJ_ID" --scope "$KV_SCOPE"

echo "Workload identity created and assigned Key Vault access."

echo "App clientId: $APP_ID"