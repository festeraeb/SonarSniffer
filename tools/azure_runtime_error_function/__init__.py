import logging
import os
import json
import uuid
from datetime import datetime

import azure.functions as func
from azure.storage.blob import BlobServiceClient

# Environment variables expected:
# - AZURE_STORAGE_CONNECTION_STRING : connection string for a storage account
# - RUNTIME_ERROR_CONTAINER : container name to store reports (default: 'runtime-errors')

CONTAINER = os.environ.get("RUNTIME_ERROR_CONTAINER", "runtime-errors")
STORAGE_CONN = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

if STORAGE_CONN:
    blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN)
    try:
        container_client = blob_service.get_container_client(CONTAINER)
        if not container_client.exists():
            container_client.create_container()
    except Exception:
        # Defer errors to runtime; we'll attempt to create on demand
        container_client = None
else:
    blob_service = None
    container_client = None


def save_payload_to_blob(payload: dict) -> str:
    """Save payload JSON to a blob and return blob name."""
    if not blob_service:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING not configured")

    container = blob_service.get_container_client(CONTAINER)
    # ensure container exists
    try:
        if not container.exists():
            container.create_container()
    except Exception:
        pass

    name = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex + ".json"
    blob = container.get_blob_client(name)
    blob.upload_blob(json.dumps(payload, indent=2), overwrite=True, content_settings=None)
    return name


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Runtime error function invoked")
    try:
        payload = req.get_json()
    except Exception as ex:
        logging.exception("Bad request: cannot parse JSON")
        return func.HttpResponse("Invalid JSON", status_code=400)

    try:
        blob_name = save_payload_to_blob(payload)
        logging.info("Saved runtime error to blob: %s", blob_name)
        return func.HttpResponse(json.dumps({"ok": True, "blob": blob_name}), status_code=200, mimetype="application/json")
    except Exception as ex:
        logging.exception("Failed to store payload: %s", ex)
        return func.HttpResponse("Internal server error", status_code=500)
