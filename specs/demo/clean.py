import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Configuration
ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL')
BUCKET_NAME = os.getenv('R2_BUCKET_NAME')

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm not found. Install it for a progress bar: pip install tqdm")
    # Fallback dummy tqdm
    class tqdm:
        def __init__(self, total=None, unit='it'):
            self.total = total
            self.n = 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, n=1):
            self.n += n
            if self.total:
                print(f"Progress: {self.n}/{self.total}", end='\r')
            else:
                print(f"Progress: {self.n}", end='\r')

def get_s3_client():
    """Create and return an S3 client for R2."""
    if not all([ACCESS_KEY, SECRET_KEY, ENDPOINT_URL, BUCKET_NAME]):
        raise ValueError("Missing R2 configuration in .env file. Please check R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME.")
    
    return boto3.client('s3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

def delete_batch(client, bucket, keys):
    """Delete a batch of keys from S3."""
    if not keys:
        return 0
    try:
        response = client.delete_objects(
            Bucket=bucket,
            Delete={
                'Objects': [{'Key': k} for k in keys],
                'Quiet': True
            }
        )
        # Check for errors
        if 'Errors' in response:
            for err in response['Errors']:
                print(f"Failed to delete {err['Key']}: {err['Code']}")
            return len(keys) - len(response['Errors'])
        return len(keys)
    except ClientError as e:
        print(f"Error deleting batch: {e}")
        return 0

def clean_r2_folder(prefix='aitrading/'):
    """
    Clean all files in the specified R2 bucket with the given prefix.
    
    Args:
        prefix (str): The folder prefix to clean. Defaults to 'aitrading/'.
    """
    try:
        s3 = get_s3_client()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return

    print(f"Connecting to R2 bucket '{BUCKET_NAME}'...")
    print(f"Target prefix: '{prefix}'")
    
    # 1. List all objects first
    print("Scanning for files (this may take a moment)...")
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
        
        keys_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    keys_to_delete.append(obj['Key'])
    except Exception as e:
        print(f"Error scanning bucket: {e}")
        return
                
    total_files = len(keys_to_delete)
    
    if total_files == 0:
        print(f"No files found with prefix '{prefix}'.")
        return

    print(f"\nFound {total_files} files to delete.")
    print("Examples:")
    for k in keys_to_delete[:3]:
        print(f" - {k}")
    if total_files > 3:
        print(" ...")

    # 2. Confirmation
    confirm = input(f"\nAre you sure you want to PERMANENTLY DELETE these {total_files} files? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return

    # 3. Delete in batches
    batch_size = 1000 # S3 limit
    batches = [keys_to_delete[i:i + batch_size] for i in range(0, total_files, batch_size)]
    
    print(f"\nDeleting {total_files} files in {len(batches)} batches...")
    
    deleted_count = 0
    with tqdm(total=total_files, unit='file') as pbar:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for batch in batches:
                future = executor.submit(delete_batch, s3, BUCKET_NAME, batch)
                futures.append(future)
            
            for future in futures:
                count = future.result()
                deleted_count += count
                if hasattr(pbar, 'update'):
                    pbar.update(len(batches[futures.index(future)])) # Update by batch size
                
    print(f"\nCleanup completed! Deleted {deleted_count} files.")

if __name__ == "__main__":
    # 修改这里：去掉重复的 bucket 名字，只保留桶内的实际路径
    # 根据截图，实际路径应该是：aitrading/runs/
    target_path = "aitrading/runs/"
    
    print(f"!!! 警告 !!!")
    print(f"即将清理路径: {target_path} 下的所有内容")
    
    # 执行删除
    clean_r2_folder(prefix=target_path)