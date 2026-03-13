import pymysql

# Database connection details
# URL: mysql+pymysql://root:Prasant2457%40@localhost/careloop
host = "localhost"
user = "root"
password = "Prasant2457@"
database = "careloop"

def migrate():
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = connection.cursor()
        
        # Check if the column exists
        cursor.execute("SHOW COLUMNS FROM medicines LIKE 'is_taken'")
        result = cursor.fetchone()
        
        if not result:
            print("Adding 'is_taken' column to 'medicines' table...")
            cursor.execute("ALTER TABLE medicines ADD COLUMN is_taken BOOLEAN DEFAULT FALSE")
            connection.commit()
            print("Migration successful: 'is_taken' column added.")
        else:
            print("'is_taken' column already exists in 'medicines' table.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == "__main__":
    migrate()
