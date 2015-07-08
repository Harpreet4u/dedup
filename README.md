# dedup
DeDup file storage

## REST API

Three calls for uploading, downloading and deleting files.

1. Uploading files

POST: http://localhost:8888/upload

For testing go to: http://localhost:8888/

Returns: 
    
    Json Response:
        
        {"status": "success/failure", "reponse_id": "file id"}

2. Downloading files

GET: http://localhost:8888/download?id="file id here"

Returns:

    Json Response if downloading fails:

        {"status": "File does not exists/Enter file id"}

   
3. Deleting files:

GET: http://localhost:8888?id="file id here"

    Json Response:

        {"status": "success/failure"}


## Backend

Uses Redis as backend to store file path on disk, timestamp and file hash.
It uses two redis hashes:

1. File Key:

    Used to store hash keys like file path (fp), timestamp (ts) and file hash (fh) using sha1.
    
    Pattern:

        Key: file:87697876979769 --> "fp" "uploads/abc.pdf" | "ts" "876876" | "fh" "98756789856984656986khjqwfd87"

2. File Hash Key:

    Used to store count of dup files (cnt) and file path (fp).

    Pattern:

        Key: fh:98756789856984656986khjqwfd87 --> "fp" "uploads/abc.pdf" | "cnt" 3

        count decreasing as duplicate files are deleted and finally file is deleted when count is 1.
