import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import psycopg
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from openai import AzureOpenAI

load_dotenv()

def test_blob():
    svc = BlobServiceClient.from_connection_string(os.environ["AZURE_STORAGE_CONNECTION_STRING"])
    for c in [
        os.environ.get("AZURE_STORAGE_CONTAINER_INBOX", "inbox"),
        os.environ.get("AZURE_STORAGE_CONTAINER_ARTEFACTS", "artefacts"),
        os.environ.get("AZURE_STORAGE_CONTAINER_LOGS", "logs"),
    ]:
        svc.get_container_client(c).get_container_properties()
    print("OK Blob Storage OK")

def test_postgres():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1;")
            cur.fetchone()
    print("OK PostgreSQL OK")

def test_docintel():
    client = DocumentIntelligenceClient(
        endpoint=os.environ["AZURE_DOCINTEL_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_DOCINTEL_KEY"]),
    )
    print("OK Document Intelligence client OK")

def test_aoai():
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    )

    resp = client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        messages=[{"role": "user", "content": "Say OK"}],
        max_tokens=5,
    )
    print("OK Azure OpenAI OK:", resp.choices[0].message.content)

if __name__ == "__main__":
    test_blob()
    test_postgres()
    test_docintel()
    test_aoai()

