#!/usr/bin/env python3

import streamlit as st
import pandas as pd
import requests
import csv
import json
import re
from typing import List, Dict, Any
from datetime import datetime

class NFTMetadataExtractor:
    def __init__(self, api_key: str, wallet_address: str):
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.base_url = "https://api.helius.xyz/v0"

    def get_nft_assets(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/addresses/{self.wallet_address}/nfts"
        params = {'api-key': self.api_key, 'page': 1, 'limit': 1000}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching NFTs: {e}")
            return []

    def filter_nfts_by_year(self, nfts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered_nfts = []
        year_pattern = re.compile(r'^(199[0-9]|20[01][0-9]|202[0-5])')
        for nft in nfts:
            name = ''
            if 'content' in nft and 'metadata' in nft['content']:
                metadata = nft['content']['metadata']
                name = metadata.get('name') or metadata.get('title', '')
            if not name and 'content' in nft:
                name = nft['content'].get('name', '')
            if not name:
                name = nft.get('name', '')
            if name and year_pattern.match(str(name)):
                filtered_nfts.append(nft)
        return filtered_nfts

    def flatten_metadata(self, nft: Dict[str, Any]) -> Dict[str, Any]:
        flattened = {}
        flattened['mint_address'] = nft.get('id', '')
        flattened['owner'] = nft.get('ownership', {}).get('owner', '')
        flattened['frozen'] = nft.get('ownership', {}).get('frozen', False)
        flattened['delegated'] = nft.get('ownership', {}).get('delegated', False)
        content = nft.get('content', {})
        metadata = content.get('metadata', {})
        flattened['name'] = metadata.get('name', '')
        flattened['symbol'] = metadata.get('symbol', '')
        flattened['description'] = metadata.get('description', '')
        flattened['image'] = metadata.get('image', '')
        flattened['animation_url'] = metadata.get('animation_url', '')
        flattened['external_url'] = metadata.get('external_url', '')
        attributes = metadata.get('attributes', [])
        if isinstance(attributes, list):
            for i, attr in enumerate(attributes):
                if isinstance(attr, dict):
                    trait_type = attr.get('trait_type', f'attribute_{i}')
                    value = attr.get('value', '')
                    clean_trait = re.sub(r'[^\w\s-]', '', str(trait_type)).strip().replace(' ', '_')
                    flattened[f'trait_{clean_trait}'] = value
        grouping = nft.get('grouping', [])
        for group in grouping:
            if group.get('group_key') == 'collection':
                flattened['collection_address'] = group.get('group_value', '')
                break
        royalty = nft.get('royalty', {})
        flattened['royalty_percent'] = royalty.get('percent', 0)
        flattened['royalty_locked'] = royalty.get('locked', False)
        supply = nft.get('supply', {})
        flattened['supply_print_max_supply'] = supply.get('print_max_supply', 0)
        flattened['supply_print_current_supply'] = supply.get('print_current_supply', 0)
        flattened['supply_edition_nonce'] = supply.get('edition_nonce', '')
        for key, value in metadata.items():
            if key not in ['name', 'symbol', 'description', 'image', 'animation_url', 'external_url', 'attributes']:
                clean_key = re.sub(r'[^\w\s-]', '', str(key)).strip().replace(' ', '_')
                flattened[f'metadata_{clean_key}'] = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        return flattened

    def export_to_csv(self, nfts: List[Dict[str, Any]], filename: str = None):
        if not nfts:
            st.warning("No NFTs to export")
            return None
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nft_metadata_{timestamp}.csv"
        flattened_nfts = []
        all_fields = set()
        for nft in nfts:
            flattened = self.flatten_metadata(nft)
            flattened_nfts.append(flattened)
            all_fields.update(flattened.keys())
        fieldnames = sorted(all_fields)
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for nft in flattened_nfts:
                row = {field: nft.get(field, '') for field in fieldnames}
                writer.writerow(row)
        return filename

def main():
    st.title("NFT Metadata Extractor for Solana Wallet")
    st.markdown("Fetch and export NFTs from your wallet by year (1990-2025).")
    api_key = st.text_input("Helius API Key", type="password")
    wallet_address = st.text_input("Solana Wallet Address")
    if st.button("Fetch NFTs"):
        if not api_key or not wallet_address:
            st.error("Please provide both API Key and Wallet Address.")
            return
        extractor = NFTMetadataExtractor(api_key, wallet_address)
        nfts = extractor.get_nft_assets()
        if not nfts:
            st.warning("No NFTs found or an error occurred.")
            return
        st.success(f"Found {len(nfts)} NFTs. Filtering by year 1990-2025...")
        filtered_nfts = extractor.filter_nfts_by_year(nfts)
        if not filtered_nfts:
            st.warning("No NFTs found with names starting with years 1990-2025.")
            return
        st.success(f"{len(filtered_nfts)} NFTs matched.")
        filename = extractor.export_to_csv(filtered_nfts)
        if filename:
            st.success(f"Export complete: {filename}")
            df = pd.read_csv(filename)
            st.dataframe(df)
            with open(filename, "rb") as f:
                st.download_button("Download CSV", data=f, file_name=filename, mime="text/csv")

if __name__ == "__main__":
    main()
