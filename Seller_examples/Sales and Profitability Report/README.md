# Mana Pool Sales & Profitability Reporting Script

This script provides Mana Pool sellers with a powerful command-line tool to generate comprehensive sales and profitability reports using the official Mana Pool Public API. It fetches order data within a specified date range, processes it to calculate key financial metrics, and exports the information into multiple easy-to-use formats (CSV, JSON, and PDF).

This tool is designed to give sellers deep insights into their sales performance, helping them track revenue, understand marketplace fees, and identify top-selling product sets.

## Features

- **Direct API Integration**: Connects securely to the Mana Pool `/seller/orders` endpoint.
- **Date Range Filtering**: Fetch orders for any specific period using `--start-date` and `--end-date` flags.
- **Profitability Analysis**: Automatically calculates Gross Revenue, Marketplace Fees, and Net Revenue for each order. It also calculates key performance indicators like your effective fee rate and net profit margin.
- **Multi-Format Reporting**:
    - **`detailed_transactions.csv`**: A granular, line-by-line log of every item sold, perfect for spreadsheet analysis.
    - **`sales_summary.json`**: A clean, machine-readable summary of key financial totals and top-selling products.
    - **`summary_report.pdf`**: A professional, human-readable report with high-level financial summaries and a sales breakdown by product set.
- **Set-Based Sales Breakdown**: The PDF report includes a table of your top-selling Magic: The Gathering sets, helping you identify what's most popular with your customers.
- **Robust Error Handling**: Provides clear feedback for API connection issues, authentication failures, or invalid parameters.
- **Secure Authentication**: Uses your Mana Pool email and API Access Token for secure, authorized access to your data.

---

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.7+** installed on your system.
2.  A **Mana Pool Seller Account**.
3.  A **Mana Pool API Access Token**. You can generate one from your integration settings in the Mana Pool dashboard.

---

## Setup & Installation

Follow these steps to set up the script and its dependencies.

1.  **Clone or Download the Script**

    Place the `seller_report.py` script in a new directory on your local machine.

2.  **Create a `requirements.txt` file**

    In the same directory as the script, create a file named `requirements.txt` and add the following lines:

    ```
    pandas
    requests
    tqdm
    reportlab
    python-dateutil
    ```

3.  **Install Dependencies**

    Open your terminal or command prompt, navigate to the script's directory, and run the following command to install the required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

The script is run from the command line and accepts several arguments to customize its behavior.

### Command Structure

```bash
python seller_report.py \
    --start-date <YYYY-MM-DD> \
    --end-date <YYYY-MM-DD> \
    --email <YOUR_MANAPOOL_EMAIL> \
    --token <YOUR_MANAPOOL_TOKEN> \
    [--output-dir <DIRECTORY_PATH>] \
    [--format <FORMATS>]
```

### Arguments

| Argument         | Description                                                                                             | Required | Default         |
| ---------------- | ------------------------------------------------------------------------------------------------------- | -------- | --------------- |
| `--start-date`   | The start date for the report period (format: YYYY-MM-DD).                                              | **Yes**  | N/A             |
| `--end-date`     | The end date for the report period (format: YYYY-MM-DD).                                                | **Yes**  | N/A             |
| `--email`        | The email address associated with your Mana Pool account.                                               | **Yes**  | N/A             |
| `--token`        | Your generated Mana Pool API Access Token (e.g., `mpat_...`).                                           | **Yes**  | N/A             |
| `--output-dir`   | The local directory where the generated reports will be saved.                                          | No       | `./reports`     |
| `--format`       | A comma-separated list of desired output formats. Available options: `csv`, `json`, `pdf`.              | No       | `csv,json,pdf`  |

### Example

To generate all reports for the first quarter of 2025:

```bash
python seller_report.py \
    --start-date 2025-01-01 \
    --end-date 2025-03-31 \
    --email "seller@example.com" \
    --token "mpat_your_very_secret_api_token_here"
```

---

## Generated Output

After running successfully, the script will create a directory (defaulting to `./reports`) containing the following files:

### `detailed_transactions.csv`

A comprehensive CSV file with one row for every line item sold. This is ideal for importing into Excel or Google Sheets for in-depth analysis. Columns include:
- `order_id`
- `created_at`
- `gross_revenue_usd`
- `fees_usd`
- `net_revenue_usd`
- `fee_rate_percent`
- `profit_margin_percent`
- `set_code`
- `product_name`
- `quantity`
- `price_per_item_usd`

### `sales_summary.json`

A JSON file that provides a high-level summary of your business performance, suitable for integration with other tools.

```json
{
    "total_gross_revenue_usd": 1550.75,
    "total_fees_paid_usd": 145.20,
    "total_net_revenue_usd": 1405.55,
    "total_orders": 42,
    "average_gross_revenue_per_order_usd": 36.92,
    "top_selling_products_by_quantity": {
        "Fable of the Mirror-Breaker": 15,
        "Solitude": 12,
        "...": "..."
    }
}
```

### `summary_report.pdf`

A clean, professional PDF document designed for easy viewing and printing. It contains three main sections:
1.  **Overall Profitability Summary**: A table with your key financial totals, including gross revenue, net revenue, and average profit margin.
2.  **Sales by Set**: A table ranking your top-selling product sets by total sales value, helping you see what's currently trending.
3.  **Report Information**: The date range covered by the report.