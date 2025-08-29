#!/usr/bin/env python3

import argparse
import json
import logging
import sys
import time
import os

import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
API_BASE_URL = 'https://manapool.com/api/v1'
CONFIG_FILE = 'config.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file '{CONFIG_FILE}' not found.")
        logging.error("Please create it based on the example in the README.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Could not parse '{CONFIG_FILE}'. Please ensure it is valid JSON.")
        sys.exit(1)

def ask_for_confirmation(prompt):
    while True:
        response = input(f"{prompt} [y/n]: ").lower().strip()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Invalid input. Please enter 'y' or 'n'.")

class ManaPoolBuyerAPI:
    def __init__(self, email, token):
        if not email or not token:
            raise ValueError("API email and token are required.")
        self._session = requests.Session()
        self._session.headers.update({
            'X-ManaPool-Email': email,
            'X-ManaPool-Access-Token': token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def run_optimizer(self, cart_request):
        logging.info("Sending cart to the optimizer...")
        payload = {"cart": cart_request}
        try:
            response = self._session.post(f"{API_BASE_URL}/buyer/optimizer", json=payload)
            response.raise_for_status()
            
            raw_response_text = response.text.strip()
            if not raw_response_text:
                logging.error("Optimizer returned an empty response.")
                return None

            lines = raw_response_text.split('\n')
            last_line = lines[-1]
            final_result = json.loads(last_line)

            logging.info("Optimizer returned a solution.")
            return final_result

        except requests.exceptions.HTTPError as e:
            logging.error(f"Optimizer failed: {e.response.status_code} - {e.response.text}")
            return None
        except json.JSONDecodeError:
            logging.error(f"Could not parse the final optimizer response line: {last_line}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"A network error occurred: {e}")
            return None

    def get_inventory_details(self, inventory_ids):
        if not inventory_ids:
            return []
        logging.info(f"Fetching details for {len(inventory_ids)} inventory items...")
        params = {'id': inventory_ids}
        try:
            response = self._session.get(f"{API_BASE_URL}/inventory/listings", params=params)
            response.raise_for_status()
            return response.json().get('inventory_items', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Could not fetch inventory details: {e}")
            return None
            
    def create_pending_order(self, optimized_cart, shipping_address):
        logging.info("Creating a pending order to calculate final total...")
        line_items = optimized_cart['cart']
        payload = {
            "line_items": line_items,
            "shipping_address": shipping_address
        }
        try:
            response = self._session.post(f"{API_BASE_URL}/buyer/orders/pending-orders", json=payload)
            response.raise_for_status()
            logging.info("Pending order created successfully.")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.error(f"Failed to create pending order: {e.response.status_code} - {e.response.text}")
            return None
            
    def execute_purchase(self, pending_order_id, billing_address, shipping_address):
        logging.info(f"Attempting to purchase pending order: {pending_order_id}")
        payload = {
            "payment_method": "user_credit",
            "billing_address": billing_address,
            "shipping_address": shipping_address
        }
        url = f"{API_BASE_URL}/buyer/orders/pending-orders/{pending_order_id}/purchase"
        try:
            response = self._session.post(url, json=payload)
            response.raise_for_status()
            logging.info("PURCHASE SUCCESSFUL!")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.error(f"PURCHASE FAILED: {e.response.status_code} - {e.response.text}")
            return None

def build_cart_from_decklist(filepath, preferences):
    logging.info(f"Building cart from decklist file: {filepath}")
    cart = []
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('//'):
                    continue
                parts = line.split(' ', 1)
                try:
                    if len(parts) == 2 and parts[0].isdigit():
                        quantity = int(parts[0])
                        card_name = parts[1].split('(')[0].strip()
                    else:
                        quantity = 1
                        card_name = parts[0].split('(')[0].strip()
                    if not card_name:
                        logging.warning(f"Skipping invalid line {line_num} in decklist: '{line}'")
                        continue
                    cart.append({
                        "type": "mtg_single",
                        "name": card_name,
                        "quantity_requested": quantity,
                        **preferences
                    })
                except (ValueError, IndexError):
                    logging.warning(f"Could not parse line {line_num} in decklist: '{line}'")
        return cart
    except FileNotFoundError:
        logging.error(f"Decklist file not found at: {filepath}")
        return None

def build_cart_from_skus(skus_string):
    logging.info(f"Building cart from TCGplayer SKUs: {skus_string}")
    cart = []
    try:
        sku_list = [int(sku.strip()) for sku in skus_string.split(',')]
        for sku in sku_list:
            cart.append({
                "type": "tcg_sku",
                "tcgplayer_sku_ids": [sku],
                "quantity_requested": 1
            })
        return cart
    except ValueError:
        logging.error("Invalid SKU list. Please provide a comma-separated list of numbers.")
        return None

def build_cart_from_card_name(name, quantity, preferences):
    logging.info(f"Building cart for {quantity}x {name}")
    return [{
        "type": "mtg_single",
        "name": name,
        "quantity_requested": quantity,
        **preferences
    }]

def execute_purchase_flow(api, cart_request, config, should_buy, verbose=False):
    if not cart_request:
        sys.exit(1)

    optimized_cart = api.run_optimizer(cart_request)
    if not optimized_cart:
        return

    if verbose:
        inventory_ids = [item['inventory_id'] for item in optimized_cart['cart']]
        quantity_map = {item['inventory_id']: item['quantity_selected'] for item in optimized_cart['cart']}
        
        inventory_details = api.get_inventory_details(inventory_ids)
        
        if inventory_details:
            print("\n--- 🔎 Cart Contents ---")
            for item in sorted(inventory_details, key=lambda x: x['product']['single']['name']):
                prod = item['product']['single']
                quantity = quantity_map.get(item['id'], 0)
                price = item['price_cents'] / 100
                details = f"{prod.get('set', 'N/A').upper()}, {prod.get('condition_id', 'N/A')}, {prod.get('finish_id', 'N/A')}"
                print(f"  - {quantity}x {prod.get('name', 'Unknown'):<30} [{details:<18}] @ ${price:>6.2f} ea.")
            print("------------------------")

    totals = optimized_cart.get('totals', {})
    stats = optimized_cart.get('stats', {})
    cart_items = optimized_cart.get('cart', [])

    subtotal = totals.get('subtotal_cents', 0) / 100
    shipping = totals.get('shipping_cents', 0) / 100
    seller_count = totals.get('seller_count', 0)
    total_item_count = sum(item.get('quantity_selected', 0) for item in cart_items)
    response_time_s = stats.get('response_time', 0) / 1000

    print("\n--- ✅ Optimizer Result ---")
    print(f"  Card Subtotal: ${subtotal:.2f}")
    print(f"  Est. Shipping: ${shipping:.2f}")
    print(f"   Num. Sellers: {seller_count}")
    print(f"    Total Items: {total_item_count}")
    print("----------------------------")
    print(f"  Est. Total (before tax): ${subtotal + shipping:.2f}")
    
    if response_time_s > 0:
        print("----------------------------")
        print(f"  (Optimizer completed in {response_time_s:.2f} seconds)")
    print("----------------------------\n")

    if not should_buy:
        logging.info("This was a price check only. To enable purchasing, add the --buy flag.")
        return

    if not ask_for_confirmation("Proceed to calculate final total with tax and shipping?"):
        logging.info("Purchase cancelled by user.")
        return

    pending_order = api.create_pending_order(optimized_cart, config['shipping_address'])
    if not pending_order:
        return

    final_totals = pending_order['totals']
    final_subtotal = final_totals['subtotal_cents'] / 100
    final_shipping = final_totals['shipping_cents'] / 100
    final_tax = final_totals['tax_cents'] / 100
    final_total = final_totals['total_cents'] / 100

    print("\n--- 💲 Final Confirmation ---")
    print(f"      Card Subtotal: ${final_subtotal:.2f}")
    print(f"   Shipping & Handling: ${final_shipping:.2f}")
    print(f"           Sales Tax: ${final_tax:.2f}")
    print("-------------------------------")
    print(f"         FINAL TOTAL: ${final_total:.2f}")
    print("-------------------------------")
    
    if not ask_for_confirmation("\nConfirm purchase? THIS ACTION IS IRREVERSIBLE."):
        logging.info("Purchase cancelled by user.")
        return

    purchase_result = api.execute_purchase(
        pending_order['id'],
        config['billing_address'],
        config['shipping_address']
    )
    
    if purchase_result:
        order_id = purchase_result.get('order', {}).get('id', 'N/A')
        print("\n--- 🎉 Purchase Complete! ---")
        print(f"  Your Mana Pool order ID is: {order_id}")
        print("  You will receive confirmation emails from Mana Pool shortly.")
        print("------------------------------\n")

def main():
    parser = argparse.ArgumentParser(
        description="A flexible tool to find the best price and purchase cards on Mana Pool."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--decklist', metavar='FILE', help="Path to a decklist file to purchase.")
    input_group.add_argument('--skus', metavar='"SKU,..."', help="A comma-separated list of TCGplayer SKUs to purchase.")
    input_group.add_argument('--card-name', metavar='"NAME"', help="The name of a single card to purchase.")
    
    parser.add_argument('--quantity', type=int, default=1, help="Quantity for --card-name (default: 1).")
    parser.add_argument('--buy', action='store_true', help="Enable the interactive purchasing flow after optimization.")
    parser.add_argument('--verbose', action='store_true', help="Display the full list of cards in the optimized cart.")

    args = parser.parse_args()
    
    api_token = os.getenv('MANAPOOL_API_TOKEN')
    if not api_token:
        logging.error("Security Error: MANAPOOL_API_TOKEN environment variable not set.")
        logging.error("Please set this variable to your API token to continue.")
        sys.exit(1)

    config = load_config()
    api = ManaPoolBuyerAPI(config['api_email'], api_token)

    cart_request = None
    if args.decklist:
        cart_request = build_cart_from_decklist(args.decklist, config['card_preferences'])
    elif args.skus:
        cart_request = build_cart_from_skus(args.skus)
    elif args.card_name:
        cart_request = build_cart_from_card_name(args.card_name, args.quantity, config['card_preferences'])
    
    execute_purchase_flow(api, cart_request, config, args.buy, args.verbose)

if __name__ == "__main__":
    main()