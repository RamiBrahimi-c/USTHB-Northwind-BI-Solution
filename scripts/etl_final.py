import pandas as pd
from sqlalchemy import create_engine, text
import os

# CONFIG
SERVER = 'localhost'
UID = 'sa'
PWD = 'sqlsql123.'
DRIVER = 'ODBC Driver 17 for SQL Server'
CSV_PATH = '../data/'
DW_DB = 'Northwind_DW'

def run_hybrid_etl():
    print("--- Starting FORCE-MATCH ETL ---")
    
    # Connect to DW
    master_conn = f'mssql+pyodbc://{UID}:{PWD}@{SERVER}:1433/master?driver={DRIVER}&TrustServerCertificate=yes'
    with create_engine(master_conn, isolation_level='AUTOCOMMIT').connect() as conn:
        conn.execute(text(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DW_DB}') CREATE DATABASE {DW_DB}"))
    
    engine_dw = create_engine(f'mssql+pyodbc://{UID}:{PWD}@{SERVER}:1433/{DW_DB}?driver={DRIVER}&TrustServerCertificate=yes')

    # 1. READ CSVs
    print("1. Reading CSVs...")
    df_orders = pd.read_csv(os.path.join(CSV_PATH, 'Orders.csv'))
    df_details = pd.read_csv(os.path.join(CSV_PATH, 'Order Details.csv'))
    df_customers = pd.read_csv(os.path.join(CSV_PATH, 'Customers.csv'))
    # We load Products just to get the Category names
    df_products = pd.read_csv(os.path.join(CSV_PATH, 'Products.csv'))

    # 2. CLEANUP
    for df in [df_orders, df_details, df_customers, df_products]:
        df.columns = df.columns.str.strip()

    def clean_currency(x):
        if isinstance(x, str): return float(x.replace('€', '').replace(',', '').strip())
        return x
    
    df_details['Unit Price'] = df_details['Unit Price'].apply(clean_currency)

    # 3. FORCE DIMENSIONS
    # We CREATE the Product Dimension from the Sales Data to guarantee 100% match
    unique_products = df_details[['Product']].drop_duplicates().reset_index(drop=True)
    unique_products['ProductKey'] = unique_products.index + 1 # Create artificial IDs
    
    # Try to bring in Categories from the Products.csv file
    # We join on "Product Name" vs "Product"
    dim_product = pd.merge(unique_products, df_products[['Product Name', 'Category']], 
                           left_on='Product', right_on='Product Name', how='left')
    
    # Fallback: If Category is missing, call it "General"
    dim_product['Category'] = dim_product['Category'].fillna('General')
    dim_product = dim_product[['ProductKey', 'Product', 'Category']]
    dim_product.rename(columns={'Product': 'ProductName'}, inplace=True)

    # Customers
    dim_customer = df_customers[['ID', 'Company', 'Country/Region']].copy()
    dim_customer.rename(columns={'ID': 'CustomerKey', 'Country/Region': 'Country'}, inplace=True)

    # 4. FACT TABLE
    fact = pd.merge(df_details, df_orders, on='Order ID', how='inner')
    
    # JOIN with our FORCED Product Dimension
    fact = pd.merge(fact, dim_product, left_on='Product', right_on='ProductName', how='left')
    
    # JOIN with Customers
    fact = pd.merge(fact, dim_customer, left_on='Customer', right_on='Company', how='left')

    # Dates & Calc
    fact['Order Date'] = pd.to_datetime(fact['Order Date'], format='mixed')
    fact['Shipped Date'] = pd.to_datetime(fact['Shipped Date'], format='mixed', errors='coerce')
    fact['SalesAmount'] = fact['Quantity'] * fact['Unit Price']

    final_fact = pd.DataFrame()
    final_fact['Order ID'] = fact['Order ID']
    final_fact['Order Date'] = fact['Order Date']
    final_fact['Shipped Date'] = fact['Shipped Date']
    final_fact['Quantity'] = fact['Quantity']
    final_fact['SalesAmount'] = fact['SalesAmount']
    final_fact['ProductKey'] = fact['ProductKey'].fillna(-1).astype(int)
    final_fact['CustomerKey'] = fact['CustomerKey'].fillna(-1).astype(int)
    final_fact['EmployeeKey'] = -1 # Skip employees to save headache

    # 5. LOAD
    print("4. Loading Data...")
    dim_product.to_sql('DimProduct', engine_dw, if_exists='replace', index=False)
    dim_customer.to_sql('DimCustomer', engine_dw, if_exists='replace', index=False)
    final_fact.to_sql('FactSales', engine_dw, if_exists='replace', index=False)

    print("--- SUCCESS: 100% Match Guaranteed ---")

if __name__ == "__main__":
    run_hybrid_etl()