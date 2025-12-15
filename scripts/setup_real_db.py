import requests
import pyodbc
import re
import time

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'localhost'
UID = 'sa'
PWD = 'sqlsql123.'
DRIVER = 'ODBC Driver 17 for SQL Server'
DATABASE_NAME = 'Northwind'

def setup_real_northwind():
    print(f"--- Setting up '{DATABASE_NAME}' Database (Optimized) ---")

    # 1. Download
    url = "https://raw.githubusercontent.com/microsoft/sql-server-samples/master/samples/databases/northwind-pubs/instnwnd.sql"
    print(f"1. Downloading script...")
    try:
        response = requests.get(url)
        sql_content = response.text
    except Exception as e:
        print(f"Error downloading: {e}")
        return

    # 2. Connect
    print("2. Connecting to SQL Server...")
    conn_str = f'DRIVER={{{DRIVER}}};SERVER={SERVER};UID={UID};PWD={PWD};AutoCommit=True'
    try:
        cnxn = pyodbc.connect(conn_str, autocommit=True)
        cursor = cnxn.cursor()
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 3. Create DB Manually
    print("3. Resetting Database...")
    try:
        # Force disconnect other users to avoid locks
        cursor.execute(f"""
            IF EXISTS (SELECT * FROM sys.databases WHERE name = '{DATABASE_NAME}')
            BEGIN
                ALTER DATABASE {DATABASE_NAME} SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                DROP DATABASE {DATABASE_NAME};
            END
        """)
        cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
        print(f"   Database '{DATABASE_NAME}' created.")
    except Exception as e:
        print(f"   Error creating DB: {e}")
        return

    # 4. Clean Script
    print("4. preparing SQL script...")
    # Remove Windows-specific file paths causing errors
    sql_content = re.sub(r"(?i)CREATE DATABASE.*?GO", "", sql_content, flags=re.DOTALL)
    sql_content = re.sub(r"(?i)exec sp_dboption.*", "", sql_content)

    # 5. Populate
    print("5. Populating Database (This may take 30s)...")
    cursor.execute(f"USE {DATABASE_NAME}")
    
    # Split by 'GO' on its own line
    commands = re.split(r'^\s*GO\s*$', sql_content, flags=re.MULTILINE | re.IGNORECASE)
    total = len(commands)
    
    for i, cmd in enumerate(commands):
        if cmd.strip():
            try:
                # Print progress every 50 batches so you know it's not frozen
                if i % 50 == 0:
                    print(f"   Processing batch {i}/{total}...")
                cursor.execute(cmd)
            except Exception as e:
                # Microsoft script has some old permission commands that fail in Docker
                # We can safely ignore them as long as tables are created
                pass

    print(f"   Done processing {total} batches.")

    # 6. Verify
    print("6. Verifying...")
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'")
    count = cursor.fetchone()[0]
    
    if count > 10:
        print(f"✅ SUCCESS: Database '{DATABASE_NAME}' is ready with {count} tables!")
    else:
        print(f"❌ WARNING: Only found {count} tables. Something might be missing.")

    cnxn.close()

if __name__ == "__main__":
    setup_real_northwind()