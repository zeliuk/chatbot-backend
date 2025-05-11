import os
import json
import tempfile
from dotenv import load_dotenv
from O365 import Account, FileSystemTokenBackend
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from docx import Document as DocxReader
import fitz  # PyMuPDF

load_dotenv()

SNAPSHOT_FILE = "snapshot.json"

def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except Exception:
            return {}
    return {}

def save_snapshot(snapshot):
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshot, f)

def get_onedrive_documents():
    credentials = (
        os.getenv("O365_CLIENT_ID"),
        os.getenv("O365_CLIENT_SECRET")
    )

    account = Account(
        credentials,
        tenant_id=os.getenv("O365_TENANT_ID"),
        auth_flow_type='credentials',
        token_backend=FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')
    )

    if not account.is_authenticated:
        if not account.authenticate():
            raise Exception("Authentication with Microsoft Graph failed")

    drive_id = os.getenv("ONEDRIVE_DRIVE_ID")
    folder_path = os.getenv("ONEDRIVE_FOLDER_PATH")

    storage = account.storage()
    drive = storage.get_drive(drive_id=drive_id)
    folder = drive.get_item_by_path(folder_path)
    items = folder.get_items()

    docs = []
    metadata = {}

    for file in items:
        if not file.is_file:
            continue

        ext = os.path.splitext(file.name)[-1].lower()
        if ext not in ('.txt', '.docx', '.pdf'):
            continue

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Descargar al directorio temporal
                success = file.download(to_path=temp_dir)
                if not success:
                    print(f"⚠️ No se pudo descargar: {file.name}")
                    continue

                downloaded_files = os.listdir(temp_dir)
                if not downloaded_files:
                    print(f"⚠️ No se descargó ningún archivo desde OneDrive para: {file.name}")
                    continue

                temp_path = os.path.join(temp_dir, downloaded_files[0])

                if ext == '.txt':
                    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()

                elif ext == '.docx':
                    docx = DocxReader(temp_path)
                    file_content = "\n".join([p.text for p in docx.paragraphs])

                elif ext == '.pdf':
                    pdf = fitz.open(temp_path)
                    file_content = "\n".join([page.get_text() for page in pdf])
                    pdf.close()

                doc = Document(
                    page_content=file_content,
                    metadata={
                        "source": file.name,
                        "last_modified_date_time": (
                            file.modified.strftime("%Y-%m-%dT%H:%M:%S")
                            if file.modified else "unknown"
                        )
                    }
                )
                docs.append(doc)
                metadata[file.name] = doc.metadata["last_modified_date_time"]

        except Exception as e:
            print(f"❌ Error procesando {file.name}: {e}")
            continue

    return docs, metadata

def sync_documents():
    previous_meta = load_snapshot()
    docs, current_meta = get_onedrive_documents()

    added_or_modified = [
        doc for doc in docs
        if previous_meta.get(doc.metadata["source"]) != doc.metadata.get("last_modified_date_time")
    ]

    deleted_files = [name for name in previous_meta if name not in current_meta]

    if not added_or_modified and not deleted_files:
        print("No cambios detectados.")
        return

    vectorstore = Chroma(
        persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db"),
        embedding_function=OpenAIEmbeddings()
    )

    if added_or_modified:
        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        docs_chunked = splitter.split_documents(added_or_modified)
        vectorstore.add_documents(docs_chunked)

    if deleted_files:
        vectorstore.delete(ids=deleted_files)

    save_snapshot(current_meta)
    print("✅ Vectorstore actualizado con éxito.")
