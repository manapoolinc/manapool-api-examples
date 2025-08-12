#!/usr/bin/env python3

import argparse
import csv
import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal, getcontext

import pandas as pd
import requests
from dateutil.parser import parse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from tqdm import tqdm

# --- Configuration ---
getcontext().prec = 10
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API Communication ---

class ManaPoolAPI:
    """Handles all communication with the Mana Pool API."""

    def __init__(self, email, token, api_base_url='https://manapool.com/api/v1'):
        self.base_url = api_base_url
        self._session = self._create_session(email, token)

    def _create_session(self, email, token):
        if not email or not token:
            raise ValueError("Email and Access Token are required for authentication.")
        session = requests.Session()
        session.headers.update({
            'X-ManaPool-Email': email,
            'X-ManaPool-Access-Token': token
        })
        logging.info("Session created for API communication.")
        return session

    def get_orders(self, start_date, end_date):
        """Fetches all order summaries within a given date range, handling pagination."""
        orders = []
        offset = 0
        limit = 100
        
        logging.info(f"Fetching orders from {start_date.date()} to {end_date.date()}.")

        while True:
            since_formatted = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            params = {'since': since_formatted, 'limit': limit, 'offset': offset}
            logging.info(f"Making request to /seller/orders with parameters: {params}")
            
            try:
                response = self._session.get(f"{self.base_url}/seller/orders", params=params)
                response.raise_for_status()
                
                page_orders = response.json().get('orders', [])
                if not page_orders:
                    logging.info("No more orders found on the current page. Concluding fetch.")
                    break
                
                for order in page_orders:
                    order_date = parse(order['created_at'])
                    if order_date <= end_date:
                        orders.append(order)

                if parse(page_orders[-1]['created_at']) > end_date:
                    logging.info("Last order on page is past the end date. Concluding fetch.")
                    break
                    
                offset += len(page_orders)
                time.sleep(0.5)

            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Error fetching orders: {e.response.status_code} - Response: {e.response.text}")
                return None
            except requests.exceptions.RequestException as e:
                logging.error(f"Request Error fetching orders: {e}")
                return None

        logging.info(f"Found {len(orders)} total orders in the specified date range.")
        return orders

    def get_order_details(self, order_id):
        """Retrieves full details for a single order."""
        try:
            response = self._session.get(f"{self.base_url}/seller/orders/{order_id}")
            response.raise_for_status()
            return response.json().get('order')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logging.warning(f"Order with ID {order_id} not found.")
            else:
                logging.error(f"HTTP Error for order {order_id}: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request Error for order {order_id}: {e}")
        return None

# --- Data Processing ---

def process_detailed_orders(detailed_orders):
    """
    Processes a list of detailed order data into a structured format for reporting,
    focusing on profitability and fees.
    """
    processed_data = []
    if not detailed_orders:
        return pd.DataFrame()

    logging.info("Processing detailed order data for profitability analysis...")
    for order in tqdm(detailed_orders, desc="Processing Orders"):
        payment = order.get('payment', {})
        
        # --- Profitability Calculations ---
        subtotal = Decimal(payment.get('subtotal_cents', 0)) / 100
        shipping_revenue = Decimal(payment.get('shipping_cents', 0)) / 100
        fees = Decimal(payment.get('fee_cents', 0)) / 100
        net_revenue = Decimal(payment.get('net_cents', 0)) / 100
        
        # Gross revenue is what the buyer paid you before fees (goods + shipping)
        gross_revenue = subtotal + shipping_revenue
        
        # Calculate fee rate and profit margin as percentages
        fee_rate_percent = (fees / gross_revenue * 100) if gross_revenue > 0 else Decimal('0')
        profit_margin_percent = (net_revenue / gross_revenue * 100) if gross_revenue > 0 else Decimal('0')

        for item in order.get('items', []):
            product_info = item.get('product', {})
            product_name = "N/A"
            set_code = "N/A"

            if product_info.get('single'):
                product_name = product_info['single'].get('name', 'N/A')
                set_code = product_info['single'].get('set', 'N/A')
            elif product_info.get('sealed'):
                product_name = product_info['sealed'].get('name', 'N/A')
                set_code = product_info['sealed'].get('set', 'N/A')

            processed_data.append({
                'order_id': order.get('id'),
                'created_at': parse(order['created_at']),
                'gross_revenue_usd': float(gross_revenue),
                'fees_usd': float(fees),
                'net_revenue_usd': float(net_revenue),
                'fee_rate_percent': float(fee_rate_percent),
                'profit_margin_percent': float(profit_margin_percent),
                'set_code': set_code,
                'product_name': product_name,
                'quantity': item.get('quantity'),
                'price_per_item_usd': Decimal(item.get('price_cents', 0)) / 100,
                'fulfillment_status': order.get('latest_fulfillment_status', 'N/A')
            })
    return pd.DataFrame(processed_data)

# --- Report Generation ---

def generate_sales_summary(df, output_dir):
    """Generates a high-level sales and profitability summary in JSON format."""
    if df.empty: return
    logging.info("Generating Sales Summary Report...")
    
    # Use unique orders for financial summary to avoid double-counting
    order_summary_df = df.drop_duplicates(subset='order_id').copy()
    
    total_gross_revenue = order_summary_df['gross_revenue_usd'].sum()
    total_fees = order_summary_df['fees_usd'].sum()
    total_net_revenue = order_summary_df['net_revenue_usd'].sum()
    
    summary = {
        'total_gross_revenue_usd': round(float(total_gross_revenue), 2),
        'total_fees_paid_usd': round(float(total_fees), 2),
        'total_net_revenue_usd': round(float(total_net_revenue), 2),
        'total_orders': int(order_summary_df['order_id'].nunique()),
        'average_gross_revenue_per_order_usd': round(float(order_summary_df['gross_revenue_usd'].mean()), 2),
        'top_selling_products_by_quantity': df.groupby('product_name')['quantity'].sum().nlargest(5).to_dict()
    }
    json_path = os.path.join(output_dir, 'sales_summary.json')
    with open(json_path, 'w') as f: json.dump(summary, f, indent=4, default=str)
    logging.info(f"Sales summary saved to {json_path}")

def generate_detailed_log(df, output_dir):
    """Generates a detailed transaction log as a CSV file."""
    if df.empty: return
    logging.info("Generating Detailed Transaction Log...")
    csv_path = os.path.join(output_dir, 'detailed_transactions.csv')
    df.to_csv(csv_path, index=False, date_format='%Y-%m-%d %H:%M:%S')
    logging.info(f"Detailed log saved to {csv_path}")

def generate_pdf_report(df, output_dir):
    """Generates a summary PDF report with profitability and sales-by-set breakdowns."""
    if df.empty:
        logging.warning("No data to generate PDF report.")
        return
        
    logging.info("Generating PDF summary report...")
    pdf_path = os.path.join(output_dir, 'summary_report.pdf')
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Sales & Profitability Report", styles['h1']))
    story.append(Paragraph(f"Date Range: {df['created_at'].min().date()} to {df['created_at'].max().date()}", styles['h3']))
    story.append(Spacer(1, 24))

    # --- Profitability Summary Table ---
    story.append(Paragraph("Overall Profitability Summary", styles['h2']))
    order_financials = df.drop_duplicates(subset='order_id')
    total_gross_revenue = order_financials['gross_revenue_usd'].sum()
    total_fees = order_financials['fees_usd'].sum()
    total_net_revenue = order_financials['net_revenue_usd'].sum()
    avg_fee_rate = (total_fees / total_gross_revenue * 100) if total_gross_revenue > 0 else 0
    avg_profit_margin = (total_net_revenue / total_gross_revenue * 100) if total_gross_revenue > 0 else 0

    profit_data = [
        ["Total Gross Revenue:", f"${total_gross_revenue:.2f}"],
        ["Total Marketplace Fees:", f"${total_fees:.2f}"],
        ["Total Net Revenue:", f"${total_net_revenue:.2f}"],
        ["Average Fee Rate:", f"{avg_fee_rate:.2f}%"],
        ["Average Profit Margin:", f"{avg_profit_margin:.2f}%"]
    ]
    profit_table = Table(profit_data, colWidths=[200, 150])
    profit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(profit_table)
    story.append(Spacer(1, 24))

    # --- Sales by Set Table ---
    story.append(Paragraph("Sales by Set", styles['h2']))
    df['line_item_total'] = df['price_per_item_usd'] * df['quantity']
    set_summary_df = df.groupby('set_code').agg(
        total_sales_usd=('line_item_total', 'sum'),
        units_sold=('quantity', 'sum'),
        order_count=('order_id', 'nunique')
    ).reset_index().sort_values(by='total_sales_usd', ascending=False)
    set_summary_df = set_summary_df[set_summary_df['set_code'] != 'N/A']

    if not set_summary_df.empty:
        set_data_list = [["Set Code", "Total Sales (USD)", "Units Sold", "Orders"]]
        for _, row in set_summary_df.head(15).iterrows():
            set_data_list.append([
                row['set_code'], f"${row['total_sales_usd']:.2f}",
                f"{int(row['units_sold'])}", f"{row['order_count']}"
            ])
        set_table = Table(set_data_list, colWidths=[100, 150, 100, 100])
        set_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(set_table)
    else:
        story.append(Paragraph("No set-based sales data was found.", styles['Normal']))

    doc.build(story)
    logging.info(f"PDF summary report saved to {pdf_path}")

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Generate sales and tax reports for Mana Pool sellers.")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD).")
    parser.add_argument("--output-dir", default="./reports", help="Directory to save reports.")
    parser.add_argument("--format", default="csv,json,pdf", help="Output formats (csv,json,pdf).")
    parser.add_argument("--email", required=True, help="Your Mana Pool account email.")
    parser.add_argument("--token", required=True, help="Your Mana Pool API access token.")
    
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        api = ManaPoolAPI(args.email, args.token)
        order_summaries = api.get_orders(start_date, end_date)
        if not order_summaries:
            logging.info("No orders found for the given period. Exiting.")
            return

        detailed_orders = []
        for summary in tqdm(order_summaries, desc="Fetching Order Details"):
            details = api.get_order_details(summary['id'])
            if details: detailed_orders.append(details)
            time.sleep(0.5)

        # The second argument to process_detailed_orders has been removed
        df = process_detailed_orders(detailed_orders)
        if df.empty:
            logging.warning("Processing resulted in no data. No reports will be generated.")
            return

        output_formats = [f.strip() for f in args.format.split(',')]
        if 'csv' in output_formats:
            generate_detailed_log(df, args.output_dir)
            # The generate_tax_report call is now gone
        if 'json' in output_formats:
            generate_sales_summary(df, args.output_dir)
        if 'pdf' in output_formats:
            generate_pdf_report(df, args.output_dir)
            
        logging.info("Script finished successfully.")

    except ValueError as e:
        logging.error(f"Configuration Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main()