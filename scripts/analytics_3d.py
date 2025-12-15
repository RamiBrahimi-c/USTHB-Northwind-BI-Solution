import sys
import pandas as pd
from sqlalchemy import create_engine
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# CONFIG
SERVER = 'localhost'
DATABASE = 'Northwind_DW'
UID = 'sa'
PWD = 'sqlsql123.'
DRIVER = 'ODBC Driver 17 for SQL Server'

class AnalyticsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Northwind Advanced Analytics (3D)")
        self.setGeometry(200, 200, 1000, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        lbl = QLabel("Product Performance Matrix (3D)")
        font = lbl.font()
        font.setPointSize(16)
        font.setBold(True)
        lbl.setFont(font)
        layout.addWidget(lbl)

        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        self.plot_data()

    def load_data(self):
        try:
            conn_str = f'mssql+pyodbc://{UID}:{PWD}@{SERVER}:1433/{DATABASE}?driver={DRIVER}&TrustServerCertificate=yes'
            engine = create_engine(conn_str)
            
            # Fetch Product Names directly
            query = """
            SELECT 
                p.ProductName,
                p.Category,
                f.Quantity,
                f.SalesAmount
            FROM FactSales f
            LEFT JOIN DimProduct p ON f.ProductKey = p.ProductKey
            WHERE p.ProductName IS NOT NULL 
            """
            df = pd.read_sql(query, engine)
            
            # Calculate Real Unit Price
            df['UnitPrice'] = df['SalesAmount'] / df['Quantity'].replace(0, 1)
            
            print(f"DEBUG: Loaded {len(df)} rows from SQL.")
            return df
        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()

    def plot_data(self):
        df = self.load_data()
        if df.empty: 
            print("No Data Found!")
            return

        # Group by PRODUCT (77+ points) instead of Category (8 points)
        data = df.groupby('ProductName').agg({
            'UnitPrice': 'mean', 
            'Quantity': 'sum', 
            'SalesAmount': 'sum'
        }).reset_index()

        print(f"DEBUG: Plotting {len(data)} unique products.")

        ax = self.fig.add_subplot(111, projection='3d')
        
        x = data['UnitPrice']
        y = data['Quantity']
        z = data['SalesAmount']
        
        # Scatter Plot
        # Color determined by Total Revenue (Darker = More Money)
        # Size determined by Quantity (Bigger bubble = More Items sold)
        sc = ax.scatter(x, y, z, c=z, cmap='jet', s=data['Quantity']/5, alpha=0.7, edgecolors='w')
        
        ax.set_xlabel('Unit Price (€)')
        ax.set_ylabel('Total Qty Sold')
        ax.set_zlabel('Total Revenue (€)')
        
        # Label the top 3 items so the chart looks "Analyzed"
        top_items = data.nlargest(3, 'SalesAmount')
        for i, row in top_items.iterrows():
            ax.text(row['UnitPrice'], row['Quantity'], row['SalesAmount'], 
                    row['ProductName'], size=9, weight='bold', color='black')

        self.fig.colorbar(sc, ax=ax, label='Revenue Intensity')
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AnalyticsApp()
    window.show()
    sys.exit(app.exec_())