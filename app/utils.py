import boto3
from botocore.exceptions import ClientError
import io
import os
import re
from datetime import datetime
from flask import current_app

class S3Util:
    @staticmethod
    def upload_file(file_data, object_name, bucket=None, public=False):
        """Încarcă un fișier în S3
        
        Args:
            file_data: Datele fișierului (bytes sau stream)
            object_name: Numele fișierului în S3
            bucket: Numele bucket-ului (implicit din configurație)
            public: Dacă fișierul trebuie să fie public
            
        Returns:
            URL-ul fișierului încărcat sau None în caz de eroare
        """
        # Verifică dacă configurația AWS este disponibilă
        if not current_app.config.get('AWS_ACCESS_KEY_ID') or not current_app.config.get('AWS_SECRET_ACCESS_KEY'):
            # Salvăm local în cazul în care AWS nu este configurat
            try:
                export_folder = current_app.config.get('EXPORT_FOLDER', os.path.join(current_app.root_path, '..\\exports')) # Default if not set
                file_path = os.path.join(export_folder, object_name)
                
                # Asigură-te că folderul există
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Scrie datele în fișier
                data_to_write = b''
                if isinstance(file_data, io.BytesIO):
                    file_data.seek(0)
                    data_to_write = file_data.read()
                elif isinstance(file_data, io.StringIO):
                    file_data.seek(0)
                    data_to_write = file_data.read().encode('utf-8') # Encode string to bytes
                elif isinstance(file_data, str):
                    data_to_write = file_data.encode('utf-8') # Encode string to bytes
                elif isinstance(file_data, bytes):
                    data_to_write = file_data
                else:
                    current_app.logger.error(f"Tip de date neacceptat pentru salvarea locală: {type(file_data)}")
                    return None

                with open(file_path, 'wb') as f:
                    f.write(data_to_write)
                        
                current_app.logger.info(f"AWS S3 nu este configurat. Fișier salvat local: {file_path}")
                return file_path # Returnează calea locală
            except (IOError, OSError) as e:
                current_app.logger.error(f"Eroare la salvarea locală a fișierului {object_name}: {str(e)}")
                return None
        
        bucket = bucket or current_app.config['S3_BUCKET']
        s3_client = boto3.client(
            's3',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
        )
        
        try:
            extra_args = {'ACL': 'public-read'} if public else {}
            s3_client.upload_fileobj(file_data, bucket, object_name, ExtraArgs=extra_args)
            
            if public:
                return f"https://{bucket}.s3.amazonaws.com/{object_name}"
            else:
                return s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': object_name},
                    ExpiresIn=3600
                )
        except ClientError as e:
            current_app.logger.error(f"Error uploading to S3: {str(e)}")
            return None
            
    @staticmethod
    def download_file(object_name, bucket=None):
        """Descarcă un fișier din S3
        
        Args:
            object_name: Numele fișierului în S3
            bucket: Numele bucket-ului (implicit din configurație)
            
        Returns:
            Conținutul fișierului ca bytes sau None în caz de eroare
        """
        # Verifică dacă configurația AWS este disponibilă
        if not current_app.config.get('AWS_ACCESS_KEY_ID') or not current_app.config.get('AWS_SECRET_ACCESS_KEY'):
            # Încercăm să încărcăm fișierul din sistemul local
            try:
                export_folder = current_app.config.get('EXPORT_FOLDER', os.path.join(current_app.root_path, '..\\exports')) # Default if not set
                file_path = os.path.join(export_folder, object_name)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        current_app.logger.info(f"AWS S3 nu este configurat. Fișier încărcat local: {file_path}")
                        return f.read()
                else:
                    current_app.logger.warning(f"AWS S3 nu este configurat. Fișierul local {file_path} nu a fost găsit.")
                    return None
            except (IOError, OSError) as e:
                current_app.logger.error(f"Eroare la încărcarea locală a fișierului {object_name}: {str(e)}")
                return None
        
        bucket = bucket or current_app.config['S3_BUCKET']
        s3_client = boto3.client(
            's3',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
        )
        
        try:
            response = s3_client.get_object(Bucket=bucket, Key=object_name)
            return response['Body'].read()
        except ClientError as e:
            current_app.logger.error(f"Error downloading from S3: {str(e)}")
            return None
