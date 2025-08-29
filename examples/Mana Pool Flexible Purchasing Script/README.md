# Mana Pool Flexible Purchasing Script

This script provides a powerful and flexible command-line tool to optimize and purchase Magic: The Gathering cards from Mana Pool. It is designed for buyers who want to programmatically find the best price for their cards, whether they have a full decklist, a list of TCGplayer SKUs, or just a single card in mind.

The script's core design prioritizes **user safety** through a multi-step, interactive confirmation flow, ensuring that no purchase is made without the user's explicit review and approval of the final, all-inclusive cost.

## Features

- **Flexible Input Methods**: Purchase cards using one of three convenient modes:
    - A full decklist from a local `.txt` file.
    - A comma-separated list of TCGplayer SKU IDs.
    - A specific quantity of a single card by name.
- **Powerful Cart Optimization**: Leverages the `/buyer/optimizer` endpoint to find the most efficient combination of sellers to fulfill your order based on the lowest total price.
- **Safe, Interactive Purchase Flow**: A step-by-step "wizard" that guides you through the process, with two mandatory confirmation prompts before any money is spent.
- **Configuration-Driven**: Manages user details (email, addresses, card preferences) through a simple `config.json` file, keeping the command line clean and your personal information out of the code.
- ** Detailed Cart Manifest**: Use the `--verbose` flag to display a full, detailed list of every card in the optimized cart, including its name, set, condition, and price, before you confirm the purchase.

---

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.7+** installed on your system.
2.  A **Mana Pool Buyer Account** with a payment method on file (the script uses "user_credit").
3.  A **Mana Pool API Access Token**. You can generate one from your integration settings in the Mana Pool dashboard.

---

## Security: Handling Your API Token

To protect your account, this script is designed to read your API token from an environment variable, not a command-line argument. This is a critical security practice.

**You must set the `MANAPOOL_API_TOKEN` environment variable in your terminal session before running the script.**

#### On macOS or Linux:
```bash
export MANAPOOL_API_TOKEN="mpat_your_very_secret_api_token_here"
```

#### On Windows (Command Prompt):
```bash
set MANAPOOL_API_TOKEN="mpat_your_very_secret_api_token_here"
```

#### On Windows (PowerShell):
```bash
$env:MANAPOOL_API_TOKEN="mpat_your_very_secret_api_token_here"
```

---

## Setup & Installation

Follow these steps to set up the script and its dependencies.

1.  **Clone this repo**

    Navigate to the purchasing script folder.

2.  **Create and Configure `config.json`**

    In the same directory, create a file named `config.json`. Copy the template below into the file.

    ```json
    {
        "api_email": "YOUR_MANAPOOL_EMAIL@example.com",
        "card_preferences": {
            "condition_ids": ["NM", "LP"],
            "language_ids": ["EN"],
            "finish_ids": ["NF"]
        },
        "shipping_address": {
            "name": "John Doe",
            "line1": "123 Main St",
            "city": "Anytown",
            "state": "NY",
            "postal_code": "12345",
            "country": "US"
        },
        "billing_address": {
            "name": "John Doe",
            "line1": "123 Main St",
            "city": "Anytown",
            "state": "NY",
            "postal_code": "12345",
            "country": "US"
        }
    }
    ```

    **Important:** You **must** edit this file and replace the placeholder values with your actual email, name, and addresses.

3.  **Install Dependencies**

    Open your terminal, navigate to the script's directory, and run:

    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

The script is run from the command line. You must choose one of the three input modes.

### Command Structure

```bash
python purchase.py <INPUT_MODE> [--buy] [--verbose]
```

### Arguments

| Argument          | Description                                                                                             | Required |
| ----------------- | ------------------------------------------------------------------------------------------------------- | -------- |
| `--decklist FILE` | **Input Mode:** Path to a decklist file to purchase.                                                    | **Yes**  |
| `--skus "SKU,..."`| **Input Mode:** A comma-separated list of TCGplayer SKUs to purchase (quantity 1 of each).              | **Yes**  |
| `--card-name "NAME"`| **Input Mode:** The name of a single card to purchase. Use with `--quantity`.                         | **Yes**  |
| `--quantity N`    | The quantity for the `--card-name` mode. Defaults to 1.                                                 | No       |
| `--buy`           | Enables the interactive purchasing flow. If omitted, the script will only perform a price check.        | No       |
| `--verbose`    | Display the full list of cards and their details in the optimized cart before the financial summary. | No       |

### Examples

**1. Price-Checking a Decklist (No Purchase)**

This is the safest way to start. It will run the optimizer and show you the estimated total without prompting you to buy.

```bash
python purchase.py --decklist ./path/to/my_deck.txt
```

**2. Buying a Decklist with Full Cart Details**

This will first display a detailed manifest of every card in the proposed cart, then guide you through the two-step confirmation process.

```bash
python purchase.py --decklist ./path/to/my_deck.txt --buy --verbose
```

**3. Buying from a List of TCGplayer SKUs**

```bash
python purchase.py --skus "490382,517625,263135" --buy
```

**4. Buying Four Copies of a Single Card**

```bash
python purchase.py --card-name "Solitude" --quantity 4 --buy
```

---

## The Interactive Purchase Flow

When you use the `--buy` flag, the script will guide you through a safe, two-step confirmation process.

**Checkpoint 1: Optimizer Result**
First, the script shows you the estimated cost before tax. If you use the `--verbose` flag, a detailed list of the cart contents will be displayed just before this summary. You must agree to proceed.

```
--- 🔎 Cart Contents ---
  - 1x Anzrag, the Quake-Mole      [MKM, NM, NF]        @ $ 12.00 ea.
  - 1x Delney, Streetwise Lookout  [MKM, NM, NF]        @ $ 15.75 ea.
------------------------

--- ✅ Optimizer Result ---
  Card Subtotal: $27.75
  Est. Shipping: $1.00
   Num. Sellers: 1
----------------------------
  Est. Total (before tax): $28.75
----------------------------

Proceed to calculate final total with tax and shipping? [y/n]:
```

**Checkpoint 2: Final Confirmation**
Next, the script creates a pending order to get the final, all-inclusive price. You must give one final confirmation before your account is charged.

```
--- 💲 Final Confirmation ---
      Card Subtotal: $27.75
   Shipping & Handling: $1.00
           Sales Tax: $2.32
-------------------------------
         FINAL TOTAL: $31.07
-------------------------------

Confirm purchase? THIS ACTION IS IRREVERSIBLE. [y/n]:
```