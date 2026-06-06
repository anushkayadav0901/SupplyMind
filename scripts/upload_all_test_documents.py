import os
import urllib.request
import uuid
from pathlib import Path

def upload_file(file_path, url):
    boundary = uuid.uuid4().hex
    filename = os.path.basename(file_path)
    
    with open(file_path, "rb") as f:
        file_content = f.read()
        
    # Build multipart form-data body
    body = []
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode("utf-8"))
    body.append(b"Content-Type: application/pdf")
    body.append(b"")
    body.append(file_content)
    body.append(f"--{boundary}--".encode("utf-8"))
    body.append(b"")
    
    payload = b"\r\n".join(body)
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(payload))
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            print(f"[SUCCESS] Successfully uploaded {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to upload {filename}: {e}")

def main():
    docs_dir = Path(r"d:\SupplyMind\data\test_documents")
    upload_url = "http://127.0.0.1:8000/api/v1/documents/upload"
    
    print("Starting upload of test documents to backend API...")
    for file_path in docs_dir.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]:
            print(f"Uploading {file_path.name}...")
            upload_file(str(file_path), upload_url)
    print("Completed processing of all test documents.")

if __name__ == "__main__":
    main()
