#!/usr/bin/env python3

import argparse
import logging
import sys
import pandas as pd
import requests
from tqdm import tqdm
import json
import os
import time

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
PRICES_URL = 'https://manapool.com/api/v1/prices/singles'
CACHE_FILE = 'price_cache.json'
CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours

def _parse_json_to_dataframe(json_content):
    """A helper function to parse raw JSON bytes into a pandas DataFrame."""
    try:
        full_json_data = json.loads(json_content)
        card_records = full_json_data.get('data', [])
        return pd.DataFrame(card_records)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON data: {e}")
        return None

def fetch_and_cache_prices():
    """
    Fetches the complete list of single card prices from the API and saves it to a cache file.
    """
    logging.info(f"Fetching live card prices from Mana Pool...")
    logging.info("This is a large data file, download may take a moment.")

    try:
        response = requests.get(PRICES_URL, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024

        with tqdm(
            total=total_size, unit='iB', unit_scale=True, desc="Downloading Prices"
        ) as pbar:
            content = b""
            for chunk in response.iter_content(chunk_size=block_size):
                content += chunk
                pbar.update(len(chunk))
        
        # Save the freshly downloaded content to the cache file
        logging.info(f"Saving new data to cache file: '{CACHE_FILE}'")
        with open(CACHE_FILE, 'wb') as f:
            f.write(content)

        return _parse_json_to_dataframe(content)

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download price data: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during fetch: {e}")
        return None

def get_price_data(force_update=False):
    """
    The main data retrieval function. Decides whether to use the cache or fetch new data.
    """
    if force_update:
        logging.info("Force update requested, bypassing cache.")
        return fetch_and_cache_prices()

    if os.path.exists(CACHE_FILE):
        file_age_seconds = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age_seconds < CACHE_DURATION_SECONDS:
            logging.info(f"Using fresh cache from '{CACHE_FILE}' (less than 24 hours old).")
            try:
                with open(CACHE_FILE, 'rb') as f:
                    content = f.read()
                return _parse_json_to_dataframe(content)
            except Exception as e:
                logging.error(f"Could not read cache file, fetching new data. Error: {e}")
                return fetch_and_cache_prices()
        else:
            logging.info(f"Cache file '{CACHE_FILE}' is stale (older than 24 hours).")
            return fetch_and_cache_prices()
    else:
        logging.info(f"Cache file '{CACHE_FILE}' not found.")
        return fetch_and_cache_prices()

def find_top_cards(df, set_code, count):
    """
    Filters the DataFrame for a specific set and finds the most valuable cards.
    """
    if df is None or df.empty:
        logging.error("Price data is not available to analyze.")
        return

    logging.info(f"Finding top {count} most valuable cards for set: {set_code.upper()}")

    set_df = df[df['set_code'].str.upper() == set_code.upper()].copy()

    if set_df.empty:
        logging.warning(f"No cards found for set '{set_code}'. Please check the set code.")
        return

    set_df['price_cents_nm'] = set_df['price_cents_nm'].fillna(0)
    top_cards = set_df.sort_values(by='price_cents_nm', ascending=False).head(count)

    print("\n" + "="*80)
    print(f"  Top {len(top_cards)} Most Valuable Cards in {set_code.upper()}")
    print(f"  (Based on Near Mint Non-Foil Prices)")
    print("="*80)

    if top_cards['price_cents_nm'].sum() == 0:
        print("\nNo priced cards found for this set.")
    else:
        for _, card in top_cards.iterrows():
            price_usd = card['price_cents_nm'] / 100
            
            print(f"- {card['name']:<35} | ${price_usd:>6.2f} | {card['url']}")
    
    print("="*80 + "\n")

def main():
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(
        description="Find the most valuable cards from a specific Magic: The Gathering set based on live Mana Pool prices.",
        epilog="Example: python top_cards.py --set MKM"
    )
    parser.add_argument(
        '--set',
        metavar='SET_CODE',
        required=True,
        help="The three-letter code for the set to analyze (e.g., 'MKM', 'OTJ')."
    )
    parser.add_argument(
        '--count',
        metavar='N',
        type=int,
        default=20,
        help="The number of top cards to display (default: 20)."
    )
    parser.add_argument(
        '--force-update',
        action='store_true',
        help="Bypass the cache and force a download of the latest price data."
    )
    
    args = parser.parse_args()

    price_df = get_price_data(force_update=args.force_update)
    if price_df is not None:
        find_top_cards(price_df, args.set, args.count)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()