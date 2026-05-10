import os
import io
import psycopg2
from PIL import Image
from dotenv import load_dotenv

# Load the variables from .env into the environment
load_dotenv()

def display_image_from_db(image_id):
    # Retrieve credentials from environment variables
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")

    # Establish connection
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_pass,
        host=db_host,
        port=db_port
    )
    
    try:
        cur = conn.cursor()
        
        # Updated table and column names
        query = "SELECT file_data FROM media_files WHERE file_id = 4;"
        cur.execute(query, (image_id,))
        record = cur.fetchone()
        
        if record is None:
            print("No image found with that ID in media_files.")
            return

        # Fetch the BYTEA data
        image_bytes = record[0]
        
        # Convert bytes to a stream and open with Pillow
        image_stream = io.BytesIO(image_bytes)
        img = Image.open(image_stream)
        
        # This will open the image in your default system viewer
        img.show()

    except Exception as e:
        print("Error reading image:", e)
    
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Example ID
    display_image_from_db(1)