import sys
import pandas as pd
from sqlalchemy import create_engine
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QFrame, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import calendar
import numpy as np

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'localhost'
DATABASE = 'Northwind_DW'
UID = 'sa'
PWD = 'sqlsql123.'
DRIVER = 'ODBC Driver 17 for SQL Server'

def load_data():
    try:
        conn_str = f'mssql+pyodbc://{UID}:{PWD}@{SERVER}:1433/{DATABASE}?driver={DRIVER}&TrustServerCertificate=yes'
        engine = create_engine(conn_str)
        query = """
        SELECT 
            f.[Order ID] as OrderID,
            f.[Order Date] as OrderDate,
            f.[Shipped Date] as ShippedDate,
            p.Category,
            c.Company as Client,
            c.Country as ClientCountry,
            f.SalesAmount
        FROM FactSales f
        LEFT JOIN DimProduct p ON f.ProductKey = p.ProductKey
        LEFT JOIN DimCustomer c ON f.CustomerKey = c.CustomerKey
        """
        df = pd.read_sql(query, engine)
        
        # Data Cleanup
        df['OrderDate'] = pd.to_datetime(df['OrderDate'])
        df['ShippedDate'] = pd.to_datetime(df['ShippedDate'], errors='coerce')
        df['Year'] = df['OrderDate'].dt.year
        df['Month'] = df['OrderDate'].dt.month_name()
        
        # FIX: Fill missing categories so they show up in the chart
        df['Category'] = df['Category'].fillna('Unknown')
        
        return df
    except Exception as e:
        print(f"DB Error: {e}")
        return pd.DataFrame()

# ==========================================
# UI COMPONENTS
# ==========================================
class KPI_Card(QFrame):
    def __init__(self, title, value, color):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"background-color: {color}; border-radius: 8px; color: white;")
        layout = QVBoxLayout()
        t = QLabel(title)
        t.setFont(QFont("Arial", 10))
        layout.addWidget(t)
        self.val_lbl = QLabel(value)
        self.val_lbl.setFont(QFont("Arial", 15, QFont.Bold))
        layout.addWidget(self.val_lbl)
        self.setLayout(layout)
    
    def setValue(self, text):
        self.val_lbl.setText(text)

class NorthwindApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Northwind Analytics Suite (Linux)")
        self.setGeometry(50, 50, 1300, 800)
        
        self.df = load_data()
        if self.df.empty: sys.exit()

        main_w = QWidget()
        self.setCentralWidget(main_w)
        main_l = QHBoxLayout(main_w)

        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("background-color: #2C3E50; color: white;")
        sb_l = QVBoxLayout(sidebar)
        sb_l.setAlignment(Qt.AlignTop)
        
        title = QLabel("NORTHWIND BI")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        sb_l.addWidget(title)
        sb_l.addSpacing(30)

        # Filters
        self.cb_year = QComboBox()
        self.cb_year.addItem("All Years")
        self.cb_year.addItems(sorted(self.df['Year'].unique().astype(str)))
        self.cb_year.currentTextChanged.connect(self.update_ui)
        
        self.cb_month = QComboBox()
        self.cb_month.addItem("All Months")
        self.cb_month.addItems(list(calendar.month_name)[1:])
        self.cb_month.currentTextChanged.connect(self.update_ui)

        self.cb_country = QComboBox()
        self.cb_country.addItem("All Countries")
        self.cb_country.addItems(sorted(self.df['ClientCountry'].dropna().unique()))
        self.cb_country.currentTextChanged.connect(self.update_ui)

        for cb, l in [(self.cb_year,"Year"), (self.cb_month,"Month"), (self.cb_country,"Country")]:
            cb.setStyleSheet("color: black; background: white; padding: 5px;")
            sb_l.addWidget(QLabel(l))
            sb_l.addWidget(cb)
            sb_l.addSpacing(15)

        sb_l.addStretch()
        sb_l.addWidget(QLabel("Data Source: SQL Server"))
        main_l.addWidget(sidebar)

        # --- DASHBOARD CONTENT ---
        content_l = QVBoxLayout()
        
        # 1. KPIs
        kpi_l = QHBoxLayout()
        self.kpi1 = KPI_Card("Total Revenue", "0", "#27AE60")
        self.kpi2 = KPI_Card("Orders > $500", "0", "#E67E22")
        self.kpi3 = KPI_Card("Est. Tax (10%)", "0", "#C0392B")
        self.kpi4 = KPI_Card("Total Orders", "0", "#2980B9")
        
        for k in [self.kpi1, self.kpi2, self.kpi3, self.kpi4]: kpi_l.addWidget(k)
        content_l.addLayout(kpi_l)

        # 2. Charts Grid
        grid = QGridLayout()
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        def create_chart():
            fig = plt.figure()
            cv = FigureCanvas(fig)
            cv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            return fig, cv

        self.fig1, self.cv1 = create_chart()
        grid.addWidget(self.cv1, 0, 0)
        
        self.fig2, self.cv2 = create_chart()
        grid.addWidget(self.cv2, 0, 1)

        self.fig3, self.cv3 = create_chart()
        grid.addWidget(self.cv3, 1, 0)

        self.fig4, self.cv4 = create_chart()
        grid.addWidget(self.cv4, 1, 1)

        content_l.addLayout(grid, stretch=1)
        main_l.addLayout(content_l)

        self.update_ui()

    def update_ui(self):
        d = self.df.copy()
        
        # Filter Logic
        y, m, c = self.cb_year.currentText(), self.cb_month.currentText(), self.cb_country.currentText()
        if y != "All Years": d = d[d['Year'] == int(y)]
        if m != "All Months": d = d[d['Month'] == m]
        if c != "All Countries": d = d[d['ClientCountry'] == c]

        if d.empty: return

        # KPIs
        order_totals = d.groupby('OrderID')['SalesAmount'].sum()
        high_val = order_totals[order_totals >= 500]
        self.kpi1.setValue(f"€{d['SalesAmount'].sum():,.0f}")
        self.kpi2.setValue(f"{len(high_val)}")
        self.kpi3.setValue(f"€{(high_val.sum() * 0.10):,.0f}")
        self.kpi4.setValue(f"{d['OrderID'].nunique()}")

        # Chart 1: Trend
        self.fig1.clear()
        ax1 = self.fig1.add_subplot(111)
        trend = d.groupby('OrderDate')['SalesAmount'].sum().reset_index()
        if not trend.empty:
            ax1.plot(trend['OrderDate'], trend['SalesAmount'], color='#2980B9', linewidth=2)
            ax1.set_title("Revenue Trend", fontsize=10, fontweight='bold')
            self.fig1.autofmt_xdate()
            ax1.grid(True, alpha=0.3)
            self.fig1.tight_layout()
        self.cv1.draw()

        # Chart 2: Clients
        self.fig2.clear()
        ax2 = self.fig2.add_subplot(111)
        clients = d.groupby('Client')['SalesAmount'].sum().sort_values().tail(5)
        if not clients.empty:
            # Manual positioning to avoid weird scaling
            y_pos = np.arange(len(clients))
            ax2.barh(y_pos, clients.values, color='#8E44AD', height=0.6, align='center')
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(clients.index)
            ax2.set_title("Top 5 Clients", fontsize=10, fontweight='bold')
            ax2.margins(y=0.1)
            self.fig2.tight_layout()
        self.cv2.draw()

        # Chart 3: Delivery
        self.fig3.clear()
        ax3 = self.fig3.add_subplot(111)
        u_orders = d[['OrderID', 'ShippedDate']].drop_duplicates()
        delivered = u_orders['ShippedDate'].notna().sum()
        pending = u_orders['ShippedDate'].isna().sum()
        if (delivered + pending) > 0:
            ax3.pie([delivered, pending], labels=['Delivered', 'Pending'], 
                    colors=['#27AE60', '#E74C3C'], autopct='%1.1f%%', startangle=90, pctdistance=0.85)
            ax3.add_artist(plt.Circle((0,0),0.70,fc='white'))
            ax3.set_title("Delivery Status", fontsize=10, fontweight='bold')
        self.fig3.tight_layout()
        self.cv3.draw()

        # Chart 4: Categories (The Fix)
        self.fig4.clear()
        ax4 = self.fig4.add_subplot(111)
        cats = d.groupby('Category')['SalesAmount'].sum().sort_values().tail(8)
        
        # Console Debug
        print(f"DEBUG: Selected Year: {y} | Categories found: {len(cats)}")
        
        if not cats.empty:
            # Using Numpy for positions + Align Center + Margins fixes the "Big Rectangle"
            y_pos = np.arange(len(cats))
            ax4.barh(y_pos, cats.values, color='#F39C12', height=0.6, align='center')
            ax4.set_yticks(y_pos)
            ax4.set_yticklabels(cats.index)
            ax4.set_title("Revenue by Category", fontsize=10, fontweight='bold')
            ax4.margins(y=0.1) # This stops the bar from touching the top/bottom edges
            self.fig4.tight_layout()
        else:
            ax4.text(0.5, 0.5, "No Data", ha='center')
            
        self.cv4.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = NorthwindApp()
    w.show()
    sys.exit(app.exec_())