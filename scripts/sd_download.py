#!/usr/bin/env python3
"""
ScienceDirect PDF downloader using browser session cookie.
Requires: EUID cookie from Chrome (non-HttpOnly, readable via JS).
Usage: python3 sd_download.py <pdf_url> <output_path>
"""
import sys
import urllib.request
import urllib.parse
import http.cookiejar
import json
import time
import os

def download_pdf(pdf_url: str, output_path: str, euid: str) -> bool:
    """Download PDF using EUID cookie."""
    cookies = f"EUID={euid}; SD_ART_LINK_STATE=%3Ce%3E%3Cq%3Escience%3C%2Fq%3E%3Corg%3Earticle%3C%2Forg%3E%3Cz%3Etoolbar%3C%2Fz%3E%3Crdt%3E2026%2F03%2F20%2F03%3A01%3A38%3A967%3C%2Frdt%3E%3Cenc%3EN%3C%2Fenc%3E%3C%2Fe%3E"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Cookie": cookies,
        "Referer": "https://www.sciencedirect.com/",
        "Accept": "application/pdf,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    req = urllib.request.Request(pdf_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            with open(output_path, 'wb') as f:
                f.write(data)
            print(f"Downloaded {len(data)} bytes -> {output_path}")
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 sd_download.py <pdf_url> <output_path>")
        sys.exit(1)
    
    pdf_url = sys.argv[1]
    output_path = sys.argv[2]
    
    # EUID extracted from browser session
    # This needs to be refreshed for each download session
    euid = "932e491f-348e-4716-9e1b-6de270808710"  # placeholder - update from browser
    
    download_pdf(pdf_url, output_path, euid)
