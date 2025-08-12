# Mana Pool Top Cards Analyzer

This script provides a simple and efficient command-line tool to quickly identify the most valuable single cards from any Magic: The Gathering set, using live price data from the Mana Pool Public API.

The primary goal of this tool is to give you a fast, up-to-date market snapshot of a set's most desirable cards without requiring any complex setup, authentication, or manual data parsing.

## Features

- **Live Price Data**: Fetches data directly from the `/prices/singles` endpoint to ensure you get current market values.
- **Caching**:
    - Automatically saves price data to a local file (`price_cache.json`) on the first run.
    - Subsequent runs will use the cached data if it's less than 24 hours old, making them nearly instantaneous.
    - Includes a `--force-update` flag to bypass the cache and fetch live data on demand.
- **Simple and Fast Analysis**: Takes a set code (e.g., `MKM`, `OTJ`) and instantly returns a sorted list of its top-performing cards.
- **Customizable Output**: Use the `--count` argument to specify how many cards you want to see (e.g., top 10, top 20).
- **Actionable Output**: Each card listed in the results includes a direct URL to its Mana Pool page, making it easy to view or purchase.

---

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.7+** installed on your system.
2.  The ability to install Python packages using `pip`.

*(Note: This script uses a public API endpoint and does not require a Mana Pool API key or access token.)*

---

## Setup & Installation

Follow these steps to set up the script and its dependencies.

1.  **Download the Script**

    Place the `top_cards.py` script in a new directory on your local machine.

2.  **Create a `requirements.txt` file**

    In the same directory as the script, create a file named `requirements.txt` and add the following lines:

    ```
    requests
    pandas
    tqdm
    argparse
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
python top_cards.py --set <SET_CODE> [--count <N>] [--force-update]
```

### Arguments

| Argument         | Description                                                                                             | Required | Default |
| ---------------- | ------------------------------------------------------------------------------------------------------- | -------- | ------- |
| `--set`          | The three-letter code for the set you want to analyze (e.g., `MKM`, `OTJ`, `MH3`).                       | **Yes**  | N/A     |
| `--count`        | The number of top cards to display.                                                                     | No       | `20`    |
| `--force-update` | Bypasses the 24-hour cache and forces a fresh download of the price data.                               | No       | N/A     |

### Examples

**1. First-Time Use (or after 24 hours)**

The script will automatically download and cache the price data.

```bash
python top_cards.py --set OTJ
```

**2. Subsequent Runs**

If the cache is less than 24 hours old, this command will be almost instant. This example also customizes the count to show the top 10 cards.

```bash
python top_cards.py --set MKM --count 10
```

**3. Forcing a Data Refresh**

If you want the absolute latest prices before the 24-hour cache expires, use the `--force-update` flag.

```bash
python top_cards.py --set MH3 --force-update
```

---

## Example Output

After running, the script will display a clean, formatted table in your terminal. The URLs are clickable in most modern terminals.

```
INFO: Using fresh cache from 'price_cache.json' (less than 24 hours old).
INFO: Finding top 10 most valuable cards for set: MKM

================================================================================
  Top 10 Most Valuable Cards in MKM
  (Based on Near Mint Non-Foil Prices)
================================================================================
- Vein Ripper                         | $ 25.50 | https://manapool.com/card/mkm/112/vein-ripper
- Delney, Streetwise Lookout          | $ 15.75 | https://manapool.com/card/mkm/12/delney-streetwise-lookout
- Anzrag, the Quake-Mole              | $ 12.00 | https://manapool.com/card/mkm/186/anzrag-the-quake-mole
- Leyline of the Guildpact            | $  8.50 | https://manapool.com/card/mkm/217/leyline-of-the-guildpact
- Massacre Girl, Known Killer         | $  7.99 | https://manapool.com/card/mkm/99/massacre-girl-known-killer
- Undergrowth Recon                   | $  6.50 | https://manapool.com/card/mkm/180/undergrowth-recon
- Lightning Helix                     | $  5.00 | https://manapool.com/card/mkm/219/lightning-helix
- No More Lies                        | $  4.75 | https://manapool.com/card/mkm/221/no-more-lies
- Commercial District                 | $  3.50 | https://manapool.com/card/mkm/259/commercial-district
- Archdruid's Charm                   | $  3.25 | https://manapool.com/card/mkm/151/archdruids-charm
================================================================================

```