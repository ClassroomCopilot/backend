import os
from typing import Dict, List, Optional
from supabase import create_client, Client
from modules.logger_tool import initialise_logger

class StorageManager:
    def __init__(self):
        self.logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
        
        # Initialize Supabase client with service role key
        supabase_url = os.getenv("SUPABASE_BACKEND_URL")
        service_role_key = os.getenv("SERVICE_ROLE_KEY")
        
        self.supabase = create_client(supabase_url, service_role_key)
        
        # Set headers for admin operations
        self.supabase.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        
        # Set storage client headers explicitly
        self.supabase.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })

    def check_bucket_exists(self, bucket_id: str) -> bool:
        """Check if a storage bucket exists"""
        try:
            self.logger.info(f"Checking if bucket {bucket_id} exists")
            # Get list of all buckets
            buckets = self.supabase.storage.list_buckets()
            # Check if our bucket_id is in the list
            return any(bucket.name == bucket_id for bucket in buckets)
        except Exception as e:
            self.logger.error(f"Error checking bucket {bucket_id}: {str(e)}")
            return False

    def create_bucket(self, bucket_id: str, public: bool = False, file_size_limit: int = None, allowed_mime_types: List[str] = None) -> Dict:
        """Create a new storage bucket with specified settings"""
        try:
            self.logger.info(f"Creating bucket {bucket_id}")
            
            # First check if bucket already exists
            if self.check_bucket_exists(bucket_id):
                self.logger.info(f"Bucket {bucket_id} already exists")
                return {"id": bucket_id, "name": bucket_id}
            
            # Create the bucket using storage API
            bucket = self.supabase.storage.create_bucket(bucket_id)
            
            # Then update the bucket settings using our SQL function
            if file_size_limit or allowed_mime_types:
                # Format the SQL query with parameters directly
                sql_query = f"""
                select storage.create_bucket(
                    '{bucket_id}',
                    {str(public).lower()},
                    {file_size_limit if file_size_limit is not None else 'null'},
                    {f"array{allowed_mime_types}" if allowed_mime_types else 'null'}
                );
                """
                
                self.supabase.postgrest.rpc(
                    'exec_sql',
                    {'query': sql_query}
                ).execute()
            
            return bucket
        except Exception as e:
            self.logger.error(f"Error creating bucket {bucket_id}: {str(e)}")
            raise

    def list_bucket_contents(self, bucket_id: str, path: str = "") -> Dict:
        """List contents of a bucket at specified path"""
        try:
            self.logger.info(f"Listing contents of bucket {bucket_id} at path {path}")
            contents = self.supabase.storage.from_(bucket_id).list(path)
            
            # Separate files and folders
            folders = []
            files = []
            
            for item in contents:
                if item.get("id", "").endswith("/"):
                    folders.append(item)
                else:
                    files.append(item)
                    
            return {"folders": folders, "files": files}
        except Exception as e:
            self.logger.error(f"Error listing bucket contents: {str(e)}")
            raise

    def upload_file(self, bucket_id: str, file_path: str, file_data: bytes, content_type: str = None, upsert: bool = True) -> Dict:
        """Upload a file to a storage bucket"""
        try:
            self.logger.info(f"Uploading file to {bucket_id} at path {file_path}")
            file_options = {
                "content-type": content_type,
                "x-upsert": "true" if upsert else "false"
            }
            
            return self.supabase.storage.from_(bucket_id).upload(
                path=file_path,
                file=file_data,
                file_options=file_options
            )
        except Exception as e:
            self.logger.error(f"Error uploading file: {str(e)}")
            raise

    def download_file(self, bucket_id: str, file_path: str) -> bytes:
        """Download a file from a storage bucket"""
        try:
            self.logger.info(f"Downloading file from {bucket_id} at path {file_path}")
            return self.supabase.storage.from_(bucket_id).download(file_path)
        except Exception as e:
            self.logger.error(f"Error downloading file: {str(e)}")
            raise

    def delete_file(self, bucket_id: str, file_path: str) -> None:
        """Delete a file from a storage bucket"""
        try:
            self.logger.info(f"Deleting file from {bucket_id} at path {file_path}")
            self.supabase.storage.from_(bucket_id).remove([file_path])
        except Exception as e:
            self.logger.error(f"Error deleting file: {str(e)}")
            raise

    def get_public_url(self, bucket_id: str, file_path: str) -> str:
        """Get public URL for a file"""
        try:
            self.logger.info(f"Getting public URL for file in {bucket_id} at path {file_path}")
            return self.supabase.storage.from_(bucket_id).get_public_url(file_path)
        except Exception as e:
            self.logger.error(f"Error getting public URL: {str(e)}")
            raise

    def create_signed_url(self, bucket_id: str, file_path: str, expires_in: int = 3600) -> str:
        """Create a signed URL for temporary file access"""
        try:
            self.logger.info(f"Creating signed URL for file in {bucket_id} at path {file_path}")
            return self.supabase.storage.from_(bucket_id).create_signed_url(file_path, expires_in)
        except Exception as e:
            self.logger.error(f"Error creating signed URL: {str(e)}")
            raise

    def initialize_storage(self) -> Dict:
        """Initialize storage buckets and policies"""
        try:
            self.logger.info("Initializing storage buckets and policies")
            
            # Define required buckets with their configurations
            required_buckets = [
                {
                    "id": "cc.ccusers",
                    "name": "User Files",
                    "public": False,
                    "file_size_limit": 50 * 1024 * 1024,  # 50MB
                    "allowed_mime_types": [
                        "image/*",
                        "video/*",
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.ms-powerpoint",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "text/plain",
                        "text/csv",
                        "application/json"
                    ]
                },
                {
                    "id": "cc.ccschools",
                    "name": "School Files",
                    "public": False,
                    "file_size_limit": 50 * 1024 * 1024,  # 50MB
                    "allowed_mime_types": [
                        "image/*",
                        "video/*",
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.ms-powerpoint",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "text/plain",
                        "text/csv",
                        "application/json"
                    ]
                }
            ]
            
            results = []
            for bucket_config in required_buckets:
                try:
                    # Create bucket with settings
                    bucket = self.create_bucket(
                        bucket_id=bucket_config["id"],
                        public=bucket_config["public"],
                        file_size_limit=bucket_config["file_size_limit"],
                        allowed_mime_types=bucket_config["allowed_mime_types"]
                    )
                    results.append({
                        "id": bucket_config["id"],
                        "name": bucket_config["name"],
                        "status": "created" if bucket else "exists"
                    })
                except Exception as e:
                    self.logger.error(f"Error creating bucket {bucket_config['id']}: {str(e)}")
                    results.append({
                        "id": bucket_config["id"],
                        "name": bucket_config["name"],
                        "status": "error",
                        "error": str(e)
                    })
            
            return {
                "status": "success",
                "message": "Storage initialization completed",
                "buckets": results
            }
        except Exception as e:
            self.logger.error(f"Error initializing storage: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
