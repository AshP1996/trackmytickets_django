#!/usr/bin/env python3
"""
Production URL Testing Script
Tests all critical URLs on the production server to identify broken links
"""

import requests
import json
from urllib.parse import urljoin
from datetime import datetime

# Production server base URL
BASE_URL = "https://trackmyticket.luminoai.online"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_url(url, method='GET', data=None, headers=None, expected_status=None):
    """Test a single URL and return the result"""
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10, verify=True)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=10, verify=True)
        
        # Determine if the response is successful
        is_success = response.status_code < 400
        if expected_status:
            is_success = response.status_code == expected_status
        
        status_color = GREEN if is_success else RED
        
        return {
            'url': url,
            'status_code': response.status_code,
            'success': is_success,
            'response_time': response.elapsed.total_seconds(),
            'content_type': response.headers.get('Content-Type', 'N/A')
        }
    except requests.exceptions.SSLError as e:
        return {
            'url': url,
            'status_code': 'SSL_ERROR',
            'success': False,
            'error': str(e),
            'response_time': 0
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'url': url,
            'status_code': 'CONNECTION_ERROR',
            'success': False,
            'error': str(e),
            'response_time': 0
        }
    except requests.exceptions.Timeout as e:
        return {
            'url': url,
            'status_code': 'TIMEOUT',
            'success': False,
            'error': str(e),
            'response_time': 0
        }
    except Exception as e:
        return {
            'url': url,
            'status_code': 'ERROR',
            'success': False,
            'error': str(e),
            'response_time': 0
        }

def print_result(result):
    """Print a formatted result"""
    status = result.get('status_code', 'ERROR')
    url = result['url']
    
    if result['success']:
        print(f"{GREEN}✓{RESET} [{status}] {url} ({result['response_time']:.2f}s)")
    else:
        error_msg = result.get('error', 'Failed')
        print(f"{RED}✗{RESET} [{status}] {url}")
        if 'error' in result:
            print(f"  {YELLOW}Error: {error_msg}{RESET}")

def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TrackMyTickets Production URL Testing{RESET}")
    print(f"{BLUE}Server: {BASE_URL}{RESET}")
    print(f"{BLUE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    results = []
    
    # Test 1: Landing Page
    print(f"\n{BLUE}[1] Testing Landing Page{RESET}")
    result = test_url(f"{BASE_URL}/")
    print_result(result)
    results.append(result)
    
    # Test 2: Platform URLs
    print(f"\n{BLUE}[2] Testing Platform URLs{RESET}")
    platform_urls = [
        "/platform/login",
        "/platform/dashboard",
        "/platform/api/me",
    ]
    
    for path in platform_urls:
        result = test_url(f"{BASE_URL}{path}")
        print_result(result)
        results.append(result)
    
    # Test 3: Demo Organization URLs
    print(f"\n{BLUE}[3] Testing Demo Organization URLs{RESET}")
    demo_urls = [
        "/demo/login",
        "/demo/dashboard",
        "/demo/tickets",
        "/demo/admin/dashboard",
        "/demo/admin/data-sources",
        "/demo/admin/reports",
        "/demo/api/me",
    ]
    
    for path in demo_urls:
        result = test_url(f"{BASE_URL}{path}")
        print_result(result)
        results.append(result)
    
    # Test 4: TechFlow Organization URLs
    print(f"\n{BLUE}[4] Testing TechFlow Organization URLs{RESET}")
    techflow_urls = [
        "/techflow/login",
        "/techflow/dashboard",
        "/techflow/tickets",
    ]
    
    for path in techflow_urls:
        result = test_url(f"{BASE_URL}{path}")
        print_result(result)
        results.append(result)
    
    # Test 5: Static Files
    print(f"\n{BLUE}[5] Testing Static Files{RESET}")
    static_urls = [
        "/static/css/design-system.css",
        "/static/css/landing.css",
        "/static/js/dashboard.js",
    ]
    
    for path in static_urls:
        result = test_url(f"{BASE_URL}{path}")
        print_result(result)
        results.append(result)
    
    # Test 6: API Endpoints (without authentication)
    print(f"\n{BLUE}[6] Testing Public API Endpoints{RESET}")
    api_urls = [
        "/platform/api/login",  # Should return 400/405 for GET
        "/demo/api/login",      # Should return 400/405 for GET
    ]
    
    for path in api_urls:
        result = test_url(f"{BASE_URL}{path}")
        print_result(result)
        results.append(result)
    
    # Summary
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Summary{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total - successful
    
    print(f"\nTotal URLs tested: {total}")
    print(f"{GREEN}Successful: {successful}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    
    if failed > 0:
        print(f"\n{RED}Failed URLs:{RESET}")
        for result in results:
            if not result['success']:
                print(f"  - {result['url']} [{result.get('status_code', 'ERROR')}]")
                if 'error' in result:
                    print(f"    {result['error']}")
    
    print(f"\n{BLUE}{'='*80}{RESET}\n")
    
    # Save results to file
    report_file = f"/tmp/url_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'base_url': BASE_URL,
            'total_tests': total,
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)
    
    print(f"Detailed report saved to: {report_file}\n")

if __name__ == "__main__":
    main()
