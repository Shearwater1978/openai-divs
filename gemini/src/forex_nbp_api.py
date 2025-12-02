import requests
import holidays
from datetime import date, timedelta
from typing import Dict, Set, Optional

# Constants
NBP_API_URL = "http://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{start_date}/{end_date}/?format=json"

# Initialize Polish holiday calendar
pl_holidays = holidays.PL()

class NBPForexProvider:
    """
    Handles fetching and providing compliant PLN exchange rates from NBP API.
    Rates are stored internally in a dictionary: {date_str: {currency_code: rate}}
    """
    
    def __init__(self):
        # Store rates in a dict for fast lookup: {'2024-03-01': {'USD': 4.02, 'EUR': 4.30}, ...}
        self.rates_cache: Dict[str, Dict[str, float]] = {}

    def _get_previous_business_day(self, operation_date: date) -> date:
        """
        Finds the required NBP exchange rate date (T-1 business day).
        """
        target_date = operation_date - timedelta(days=1)
        
        while True:
            # Check for weekend (5=Saturday, 6=Sunday)
            is_weekend = target_date.weekday() >= 5
            
            # Check for Polish public holidays
            is_holiday = target_date in pl_holidays
            
            if not is_weekend and not is_holiday:
                return target_date
            
            # If weekend or holiday, step back one more day
            target_date -= timedelta(days=1)

    def fetch_rates_for_period(self, currency_codes: Set[str], start_date: date, end_date: date):
        """
        Fetches rates for all required currencies in the specified date range.
        Uses NBP's bulk fetching feature.
        """
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"Fetching NBP rates for period {start_str} to {end_str}...")
        
        for currency in currency_codes:
            url = NBP_API_URL.format(
                currency_code=currency,
                start_date=start_str,
                end_date=end_str
            )
            
            try:
                response = requests.get(url)
                response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
                data = response.json()
                
                # Iterate through all rates published in the period
                for rate_entry in data['rates']:
                    rate_date_str = rate_entry['effectiveDate']
                    rate_value = rate_entry['mid']
                    
                    # Store the rate in the cache, keyed by its publication date
                    if rate_date_str not in self.rates_cache:
                        self.rates_cache[rate_date_str] = {}
                        
                    self.rates_cache[rate_date_str][currency] = rate_value
                
                print(f"Successfully cached {len(data['rates'])} rates for {currency}.")

            except requests.exceptions.HTTPError as e:
                # 404 means no data for the period (e.g., if the currency wasn't traded then)
                if response.status_code == 404:
                    print(f"NBP API: No data found for {currency} in the specified period.")
                else:
                    print(f"HTTP Error fetching {currency}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred for {currency}: {e}")

    def get_compliant_rate(self, operation_date: date, currency_code: str) -> Optional[float]:
        """
        Retrieves the PIT-38 compliant rate from the cache.
        """
        # 1. Determine the required rate publication date (T-1 Business Day)
        rate_date = self._get_previous_business_day(operation_date)
        rate_date_str = rate_date.strftime('%Y-%m-%d')

        # 2. Look up the rate in the cache
        if rate_date_str in self.rates_cache and currency_code in self.rates_cache[rate_date_str]:
            return self.rates_cache[rate_date_str][currency_code]
        else:
            print(f"WARNING: Rate not found for {currency_code} on compliant date {rate_date_str}. Check cache.")
            return None

# Example of how this will be integrated into main.py
# if __name__ == '__main__':
#     import sys
#     if 'unittest' in sys.argv:
#         # Use known dates for testing compliance logic
#         test_date = date(2024, 1, 2) # Operation on Tuesday, Jan 2 (Rate should be Jan 1, which is a holiday, so Dec 29)
#         
#         provider = NBPForexProvider()
#         compliant_date = provider._get_previous_business_day(test_date)
#         print(f"Operation on {test_date} requires rate from: {compliant_date}")
#         # Dec 29, 2023 was a Friday, correct.