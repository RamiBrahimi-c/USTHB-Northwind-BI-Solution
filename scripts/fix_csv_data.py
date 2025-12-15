import pandas as pd
import random
import os
import re

# Dynamically find the data folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, '../data/')

def fix_data():
    print(f"--- Modernizing Data in {CSV_PATH} ---")
    
    # 1. Randomize Years to Modern Times (2023, 2024, 2025)
    orders_path = os.path.join(CSV_PATH, 'Orders.csv')
    try:
        df_orders = pd.read_csv(orders_path)
    except FileNotFoundError:
        print(f"ERROR: Could not find {orders_path}")
        return
    
    print("1. Updating Order Dates to 2023-2025...")
    
    def modernize_date(date_val):
        date_str = str(date_val)
        # Find any 4-digit year (starting with 19 or 20)
        new_year = str(random.choice([2023, 2024, 2025]))
        # Replace the year part safely using Regex
        return re.sub(r'(19|20)\d{2}', new_year, date_str)

    df_orders['Order Date'] = df_orders['Order Date'].apply(modernize_date)
    df_orders.to_csv(orders_path, index=False)

    # 2. Randomize Countries (For the Map/Filter)
    cust_path = os.path.join(CSV_PATH, 'Customers.csv')
    df_cust = pd.read_csv(cust_path)
    
    print("2. Diversifying Countries...")
    countries = ['USA', 'UK', 'France', 'Germany', 'Canada', 'Brazil', 'Japan', 'Australia']
    df_cust['Country/Region'] = df_cust['Country/Region'].apply(lambda x: random.choice(countries))
    df_cust.to_csv(cust_path, index=False)

    print("--- Data Successfully Modernized! ---")

if __name__ == "__main__":
    fix_data()