import os
import pandas as pd
from typing import Optional, Dict, Any, List

from src.logger import logger


class Fetch_data:


    @staticmethod
    def fetch_data_from_S3(
        bucket_name: str,
        object_key: str,
        file_format: str = "csv",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: Optional[str] = None,
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from AWS S3 bucket and return as a pandas DataFrame.
        
        CREDENTIALS REQUIRED:
        =====================
        You need the following AWS credentials to access S3:
        
        1. AWS_ACCESS_KEY_ID (Required):
           - A 20-character alphanumeric string
           - Obtained from AWS IAM (Identity and Access Management)
           - Example: 'AKIAIOSFODNN7EXAMPLE'
           - Can be set as environment variable: AWS_ACCESS_KEY_ID
           
        2. AWS_SECRET_ACCESS_KEY (Required):
           - A 40-character string with mixed characters
           - Paired with the Access Key ID
           - Example: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
           - Can be set as environment variable: AWS_SECRET_ACCESS_KEY
           
        3. AWS_REGION (Optional but recommended):
           - The AWS region where your S3 bucket is located
           - Example: 'us-east-1', 'ap-south-1', 'eu-west-1'
           - Can be set as environment variable: AWS_DEFAULT_REGION
        
        HOW TO GET CREDENTIALS:
        -----------------------
        1. Log in to AWS Console (https://console.aws.amazon.com)
        2. Go to IAM (Identity and Access Management)
        3. Navigate to Users -> Your User -> Security Credentials
        4. Click "Create Access Key"
        5. Download and securely store the credentials
        
        REQUIRED IAM PERMISSIONS:
        -------------------------
        - s3:GetObject (to read objects)
        - s3:ListBucket (to list bucket contents)
        
        RECOMMENDED: Use environment variables or AWS credentials file (~/.aws/credentials)
        instead of hardcoding credentials in code.
        
        Args:
            bucket_name (str): Name of the S3 bucket
            object_key (str): Key/path of the object within the bucket
            file_format (str): Format of the file ('csv', 'parquet', 'json', 'excel')
            aws_access_key_id (str, optional): AWS access key. Defaults to env variable.
            aws_secret_access_key (str, optional): AWS secret key. Defaults to env variable.
            aws_region (str, optional): AWS region. Defaults to env variable.
            **read_kwargs: Additional arguments passed to pandas read function
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data
            
        Raises:
            ImportError: If boto3 is not installed
            Exception: If S3 connection or data fetch fails
            
        Example:
            >>> ingestion = Data_ingestion(import_path="s3://mybucket/data.csv", 
            ...                            path_type="s3", 
            ...                            export_path="./data/", 
            ...                            schem_yaml_path="./schema.yaml")
            >>> df = ingestion.fetch_data_from_S3(
            ...     bucket_name="my-fraud-detection-bucket",
            ...     object_key="data/train_transaction.csv",
            ...     file_format="csv"
            ... )
        """
        try:
            import boto3
            from io import BytesIO, StringIO
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 access. Install it with: pip install boto3"
            )
        
        # Use environment variables if credentials not provided
        aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = aws_region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        try:
            # Create S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
            
            logger.info(f"Fetching data from S3: s3://{bucket_name}/{object_key}")
            
            # Get the object from S3
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            data = response['Body'].read()
            
            # Read data based on file format
            if file_format.lower() == "csv":
                df = pd.read_csv(BytesIO(data), **read_kwargs)
            elif file_format.lower() == "parquet":
                df = pd.read_parquet(BytesIO(data), **read_kwargs)
            elif file_format.lower() == "json":
                df = pd.read_json(BytesIO(data), **read_kwargs)
            elif file_format.lower() in ["excel", "xlsx", "xls"]:
                df = pd.read_excel(BytesIO(data), **read_kwargs)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            logger.info(f"Successfully fetched {len(df)} rows from S3")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data from S3: {str(e)}")
            raise


    @staticmethod
    def fetch_data_from_MongoDB(
        database_name: str,
        collection_name: str,
        connection_string: Optional[str] = None,
        host: str = "localhost",
        port: int = 27017,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_source: str = "admin",
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch data from MongoDB collection and return as a pandas DataFrame.
        
        CREDENTIALS REQUIRED:
        =====================
        You need the following credentials to access MongoDB:
        
        1. CONNECTION_STRING (Preferred method):
           - A complete MongoDB URI containing all connection details
           - Format: 'mongodb://[username:password@]host[:port]/[database]?[options]'
           - Example: 'mongodb://user:pass@localhost:27017/mydb?authSource=admin'
           - For MongoDB Atlas: 'mongodb+srv://user:pass@cluster.mongodb.net/mydb'
           - Can be set as environment variable: MONGODB_URI
           
        2. INDIVIDUAL CREDENTIALS (Alternative method):
           a. HOST: MongoDB server hostname
              - Default: 'localhost' for local installation
              - For Atlas: 'cluster-name.mongodb.net'
              
           b. PORT: MongoDB port number
              - Default: 27017
              
           c. USERNAME: Database username
              - Created in MongoDB or MongoDB Atlas
              
           d. PASSWORD: Database password
              - Associated with the username
              - Can be set as environment variable: MONGODB_PASSWORD
              
           e. AUTH_SOURCE: Authentication database
              - Usually 'admin' for administrative users
              - Or the specific database name
        
        HOW TO GET CREDENTIALS:
        -----------------------
        For MongoDB Atlas (Cloud):
        1. Log in to MongoDB Atlas (https://cloud.mongodb.com)
        2. Go to Database Access -> Add New Database User
        3. Create user with appropriate permissions
        4. Go to Network Access -> Add IP Address
        5. Get connection string from Connect -> Connect your application
        
        For Local MongoDB:
        1. Create user using mongosh:
           db.createUser({user: "username", pwd: "password", roles: ["readWrite"]})
        
        REQUIRED ROLES/PERMISSIONS:
        ---------------------------
        - read: For read-only access to the collection
        - readWrite: For read and write access
        - dbAdmin: For database administration
        
        Args:
            database_name (str): Name of the MongoDB database
            collection_name (str): Name of the collection to fetch data from
            connection_string (str, optional): Complete MongoDB connection URI
            host (str): MongoDB host. Defaults to 'localhost'
            port (int): MongoDB port. Defaults to 27017
            username (str, optional): MongoDB username
            password (str, optional): MongoDB password
            auth_source (str): Authentication database. Defaults to 'admin'
            query (dict, optional): MongoDB query filter. Defaults to {} (all documents)
            projection (dict, optional): Fields to include/exclude
            limit (int, optional): Maximum number of documents to fetch
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data
            
        Raises:
            ImportError: If pymongo is not installed
            Exception: If MongoDB connection or data fetch fails
            
        Example:
            >>> ingestion = Data_ingestion(import_path="mongodb://localhost:27017", 
            ...                            path_type="mongodb", 
            ...                            export_path="./data/", 
            ...                            schem_yaml_path="./schema.yaml")
            >>> df = ingestion.fetch_data_from_MongoDB(
            ...     database_name="fraud_detection",
            ...     collection_name="transactions",
            ...     query={"isFraud": 1},
            ...     limit=10000
            ... )
        """
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError(
                "pymongo is required for MongoDB access. Install it with: pip install pymongo"
            )
        
        # Use environment variable for connection string if not provided
        connection_string = connection_string or os.getenv("MONGODB_URI")
        password = password or os.getenv("MONGODB_PASSWORD")
        
        try:
            # Create MongoDB client
            if connection_string:
                client = MongoClient(connection_string)
                logger.info(f"Connecting to MongoDB using connection string")
            else:
                if username and password:
                    client = MongoClient(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        authSource=auth_source
                    )
                else:
                    client = MongoClient(host=host, port=port)
                logger.info(f"Connecting to MongoDB at {host}:{port}")
            
            # Access database and collection
            db = client[database_name]
            collection = db[collection_name]
            
            # Build cursor with query, projection, and limit
            query = query or {}
            cursor = collection.find(query, projection)
            
            if limit:
                cursor = cursor.limit(limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(list(cursor))
            
            # Remove MongoDB's _id field if present (optional)
            if '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            
            logger.info(f"Successfully fetched {len(df)} documents from MongoDB")
            
            # Close connection
            client.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data from MongoDB: {str(e)}")
            raise
    
    @staticmethod
    def fetch_data_from_Bigquery(
        query: Optional[str] = None,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        table_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        use_bqstorage_api: bool = False,
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from Google BigQuery and return as a pandas DataFrame.
        
        CREDENTIALS REQUIRED:
        =====================
        You need a Google Cloud Service Account to access BigQuery:
        
        1. SERVICE ACCOUNT JSON KEY FILE (Required):
           - A JSON file containing service account credentials
           - Contains: project_id, private_key, client_email, etc.
           - Can be set via environment variable: GOOGLE_APPLICATION_CREDENTIALS
           
           Example JSON structure:
           {
               "type": "service_account",
               "project_id": "your-project-id",
               "private_key_id": "key-id",
               "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
               "client_email": "service-account@your-project.iam.gserviceaccount.com",
               "client_id": "123456789",
               "auth_uri": "https://accounts.google.com/o/oauth2/auth",
               "token_uri": "https://oauth2.googleapis.com/token"
           }
        
        2. PROJECT_ID (Required):
           - Your Google Cloud Project ID
           - Found in Google Cloud Console
           - Example: 'my-fraud-detection-project'
           
        HOW TO GET CREDENTIALS:
        -----------------------
        1. Go to Google Cloud Console (https://console.cloud.google.com)
        2. Navigate to IAM & Admin -> Service Accounts
        3. Click "Create Service Account"
        4. Give it a name and description
        5. Grant it the "BigQuery Data Viewer" role (or BigQuery Admin for full access)
        6. Click on the created service account
        7. Go to Keys tab -> Add Key -> Create new key -> JSON
        8. Download and securely store the JSON file
        
        REQUIRED IAM ROLES:
        -------------------
        - roles/bigquery.dataViewer: View datasets and tables
        - roles/bigquery.jobUser: Run queries
        - roles/bigquery.user: Basic BigQuery access
        
        For full access:
        - roles/bigquery.admin: Full BigQuery administration
        
        ENVIRONMENT VARIABLE SETUP:
        ---------------------------
        Set the path to your credentials file:
        export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
        
        Args:
            query (str, optional): SQL query to execute. If None, fetches entire table.
            project_id (str, optional): GCP project ID. Defaults to credentials project.
            dataset_id (str, optional): BigQuery dataset ID (required if no query)
            table_id (str, optional): BigQuery table ID (required if no query)
            credentials_path (str, optional): Path to service account JSON file
            use_bqstorage_api (bool): Use BigQuery Storage API for faster reads
            **read_kwargs: Additional arguments passed to pandas.read_gbq()
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data
            
        Raises:
            ImportError: If google-cloud-bigquery is not installed
            ValueError: If neither query nor table details are provided
            Exception: If BigQuery connection or data fetch fails
            
        Example:
            >>> ingestion = Data_ingestion(import_path="bigquery://project/dataset/table", 
            ...                            path_type="bigquery", 
            ...                            export_path="./data/", 
            ...                            schem_yaml_path="./schema.yaml")
            >>> # Using a custom query
            >>> df = ingestion.fetch_data_from_Bigquery(
            ...     query="SELECT * FROM `project.dataset.table` WHERE isFraud = 1 LIMIT 10000",
            ...     project_id="my-project",
            ...     credentials_path="./credentials.json"
            ... )
            >>> # Or fetch entire table
            >>> df = ingestion.fetch_data_from_Bigquery(
            ...     project_id="my-project",
            ...     dataset_id="fraud_data",
            ...     table_id="transactions"
            ... )
        """
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
        except ImportError:
            raise ImportError(
                "google-cloud-bigquery is required for BigQuery access. "
                "Install it with: pip install google-cloud-bigquery pandas-gbq"
            )
        
        # Set credentials path from environment if not provided
        credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        try:
            # Create credentials and client
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                client = bigquery.Client(credentials=credentials, project=project_id)
                logger.info(f"Connected to BigQuery using service account credentials")
            else:
                # Use default credentials (from environment or gcloud auth)
                client = bigquery.Client(project=project_id)
                logger.info(f"Connected to BigQuery using default credentials")
            
            # Build query if not provided
            if query is None:
                if dataset_id is None or table_id is None:
                    raise ValueError(
                        "Either 'query' or both 'dataset_id' and 'table_id' must be provided"
                    )
                table_ref = f"`{project_id}.{dataset_id}.{table_id}`"
                query = f"SELECT * FROM {table_ref}"
            
            logger.info(f"Executing BigQuery query: {query[:100]}...")
            
            # Execute query and convert to DataFrame
            if use_bqstorage_api:
                try:
                    from google.cloud import bigquery_storage
                    df = client.query(query).to_dataframe(
                        bqstorage_client=bigquery_storage.BigQueryReadClient()
                    )
                except ImportError:
                    logger.warning(
                        "BigQuery Storage API not available, using standard API"
                    )
                    df = client.query(query).to_dataframe()
            else:
                df = client.query(query).to_dataframe()
            
            logger.info(f"Successfully fetched {len(df)} rows from BigQuery")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data from BigQuery: {str(e)}")
            raise

    @staticmethod
    def fetch_data_from_postgreSQL(
        query: Optional[str] = None,
        table_name: Optional[str] = None,
        host: str = "localhost",
        port: int = 5432,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None,
        schema: str = "public",
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from PostgreSQL database and return as a pandas DataFrame.
        
        CREDENTIALS REQUIRED:
        =====================
        You need the following credentials to access PostgreSQL:
        
        1. CONNECTION_STRING (Preferred method):
           - A complete PostgreSQL connection URI
           - Format: 'postgresql://[user[:password]@][host][:port]/[database]'
           - Example: 'postgresql://myuser:mypass@localhost:5432/mydb'
           - Can be set as environment variable: DATABASE_URL or POSTGRES_URI
           
        2. INDIVIDUAL CREDENTIALS (Alternative method):
           a. HOST: PostgreSQL server hostname
              - Default: 'localhost' for local installation
              - For cloud: your-instance.region.cloud-provider.com
              - Can be set as env var: POSTGRES_HOST
              
           b. PORT: PostgreSQL port number
              - Default: 5432
              - Can be set as env var: POSTGRES_PORT
              
           c. DATABASE: Database name
              - The specific database to connect to
              - Can be set as env var: POSTGRES_DB
              
           d. USERNAME: Database username
              - Created by database administrator
              - Default superuser is 'postgres'
              - Can be set as env var: POSTGRES_USER
              
           e. PASSWORD: Database password
              - Associated with the username
              - Can be set as env var: POSTGRES_PASSWORD
        
        HOW TO GET CREDENTIALS:
        -----------------------
        For Local PostgreSQL:
        1. Install PostgreSQL
        2. Create a user:
           CREATE USER myuser WITH PASSWORD 'mypassword';
        3. Create a database:
           CREATE DATABASE mydb;
        4. Grant permissions:
           GRANT ALL PRIVILEGES ON DATABASE mydb TO myuser;
           
        For AWS RDS:
        1. Go to AWS RDS Console
        2. Create a PostgreSQL instance
        3. Set master username and password during creation
        4. Get endpoint from instance details
        5. Configure security groups to allow access
        
        For Google Cloud SQL:
        1. Go to Google Cloud Console -> SQL
        2. Create PostgreSQL instance
        3. Create user in Users tab
        4. Get connection details from Overview
        5. Configure authorized networks or use Cloud SQL Proxy
        
        For Azure Database:
        1. Go to Azure Portal -> Azure Database for PostgreSQL
        2. Create server
        3. Set admin username and password
        4. Get server name from Overview
        5. Configure firewall rules
        
        REQUIRED PERMISSIONS:
        ---------------------
        - CONNECT: Permission to connect to the database
        - SELECT: Permission to query tables
        - USAGE: Permission to use schemas
        
        Grant example:
        GRANT CONNECT ON DATABASE mydb TO myuser;
        GRANT USAGE ON SCHEMA public TO myuser;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO myuser;
        
        Args:
            query (str, optional): SQL query to execute. If None, fetches entire table.
            table_name (str, optional): Table name to fetch (if query not provided)
            host (str): PostgreSQL host. Defaults to 'localhost'
            port (int): PostgreSQL port. Defaults to 5432
            database (str, optional): Database name
            username (str, optional): Database username
            password (str, optional): Database password
            connection_string (str, optional): Complete PostgreSQL connection URI
            schema (str): Database schema. Defaults to 'public'
            **read_kwargs: Additional arguments passed to pandas.read_sql()
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data
            
        Raises:
            ImportError: If psycopg2 or sqlalchemy is not installed
            ValueError: If neither query nor table_name is provided
            Exception: If PostgreSQL connection or data fetch fails
            
        Example:
            >>> ingestion = Data_ingestion(import_path="postgresql://localhost:5432/mydb", 
            ...                            path_type="postgresql", 
            ...                            export_path="./data/", 
            ...                            schem_yaml_path="./schema.yaml")
            >>> # Using a custom query
            >>> df = ingestion.fetch_data_from_postgreSQL(
            ...     query="SELECT * FROM transactions WHERE is_fraud = true LIMIT 10000",
            ...     host="localhost",
            ...     database="fraud_db",
            ...     username="analyst",
            ...     password="secure_password"
            ... )
            >>> # Or fetch entire table
            >>> df = ingestion.fetch_data_from_postgreSQL(
            ...     table_name="transactions",
            ...     connection_string="postgresql://user:pass@host:5432/db"
            ... )
        """
        try:
            from sqlalchemy import create_engine
            import psycopg2
        except ImportError:
            raise ImportError(
                "sqlalchemy and psycopg2 are required for PostgreSQL access. "
                "Install them with: pip install sqlalchemy psycopg2-binary"
            )
        
        # Get credentials from environment variables if not provided
        connection_string = connection_string or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URI")
        host = host or os.getenv("POSTGRES_HOST", "localhost")
        port = port or int(os.getenv("POSTGRES_PORT", 5432))
        database = database or os.getenv("POSTGRES_DB")
        username = username or os.getenv("POSTGRES_USER")
        password = password or os.getenv("POSTGRES_PASSWORD")
        
        try:
            # Build connection string if not provided
            if connection_string is None:
                if not all([database, username, password]):
                    raise ValueError(
                        "Either 'connection_string' or 'database', 'username', "
                        "and 'password' must be provided"
                    )
                connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            
            # Create SQLAlchemy engine
            engine = create_engine(connection_string)
            logger.info(f"Connecting to PostgreSQL database")
            
            # Build query if not provided
            if query is None:
                if table_name is None:
                    raise ValueError(
                        "Either 'query' or 'table_name' must be provided"
                    )
                query = f'SELECT * FROM "{schema}"."{table_name}"'
            
            logger.info(f"Executing PostgreSQL query: {query[:100]}...")
            
            # Execute query and convert to DataFrame
            df = pd.read_sql(query, engine, **read_kwargs)
            
            logger.info(f"Successfully fetched {len(df)} rows from PostgreSQL")
            
            # Dispose engine connection
            engine.dispose()
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data from PostgreSQL: {str(e)}")
            raise


    @staticmethod
    def fetch_data_from_local(
        file_path: Optional[str] = None,
        file_format: str = "csv",
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from local file system and return as a pandas DataFrame.
        
        This is a convenience method for loading local files without external credentials.
        
        Args:
            file_path (str, optional): Path to the file. Defaults to .import_path
            file_format (str): Format of the file ('csv', 'parquet', 'json', 'excel')
            **read_kwargs: Additional arguments passed to pandas read function
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data
            
        Example:
            >>> ingestion = Data_ingestion(
            ...     import_path="./data/train_transaction.csv", 
            ...     path_type="local", 
            ...     export_path="./processed/", 
            ...     schem_yaml_path="./schema.yaml"
            ... )
            >>> df = ingestion.fetch_data_from_local()
        """
        
        try:
            logger.info(f"Loading data from local file: {file_path}")
            
            if file_format.lower() == "csv":
                df = pd.read_csv(file_path, **read_kwargs)
            elif file_format.lower() == "parquet":
                df = pd.read_parquet(file_path, **read_kwargs)
            elif file_format.lower() == "json":
                df = pd.read_json(file_path, **read_kwargs)
            elif file_format.lower() in ["excel", "xlsx", "xls"]:
                df = pd.read_excel(file_path, **read_kwargs)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            logger.info(f"Successfully loaded {len(df)} rows from local file")
            return df
            
        except Exception as e:
            logger.error(f"Error loading local file: {str(e)}")
            raise

    