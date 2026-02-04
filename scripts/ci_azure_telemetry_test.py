import os, json, time
from azure.storage.blob import BlobServiceClient

conn = os.environ.get('AZURE_TEST_STORAGE_CONNSTR')
container = os.environ.get('AZURE_TEST_STORAGE_CONTAINER')
if not conn or not container:
    raise SystemExit('Missing AZURE_TEST_STORAGE_CONNSTR or AZURE_TEST_STORAGE_CONTAINER')

client = BlobServiceClient.from_connection_string(conn)
cont = client.get_container_client(container)
if not cont.exists():
    cont.create_container()

payload = {
    'test': 'sonarsniffer telemetry validation',
    'timestamp': time.time(),
}
name = f'test_telemetry_{int(time.time())}.json'
cont.upload_blob(name, json.dumps(payload), overwrite=True)
print('Uploaded telemetry test blob:', name)
