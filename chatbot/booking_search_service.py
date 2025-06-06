import requests
import logging
import json
from datetime import datetime, date
from flask import current_app
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BookingSearchService:
    """Service for searching bookings using external API"""

    def __init__(self):
        self.api_url = None
        self.auth_header = None
        self._load_config()

    def _load_config(self):
        """Load configuration from Flask app config"""
        try:
            self.api_url = current_app.config.get('BOOKING_SEARCH_API_URL')
            self.auth_header = current_app.config.get('BOOKING_SEARCH_API_AUTH')

            if not self.api_url or not self.auth_header:
                logger.warning("Booking search API configuration not found")
        except RuntimeError:
            # Handle case when called outside application context
            # Load from environment variables as fallback
            import os
            self.api_url = os.environ.get('BOOKING_SEARCH_API_URL', 'https://growth.treebo.be/growth-realization/custom_message/search_booking_by_phone/')
            self.auth_header = os.environ.get('BOOKING_SEARCH_API_AUTH', 'Basic c3VfdXNlcjpFN3FVazl1X2ZxOF9XQg==')
            logger.info("Loaded booking search API config from environment variables")

    def search_bookings_by_phone(self, phone_number: str, from_date: str = None) -> Dict:
        """
        Search for bookings by phone number using external API
        
        Args:
            phone_number (str): User's phone number
            from_date (str): Date to search from (YYYY-MM-DD format). Defaults to current date.
            
        Returns:
            Dict: API response containing booking data
        """
        try:
            # Use current date if from_date not provided
            if not from_date:
                from_date = date.today().strftime('%Y-%m-%d')

            # Prepare API request
            url = self.api_url
            headers = {
                'Authorization': self.auth_header,
                'Content-Type': 'application/json'
            }
            params = {
                'phone_number': phone_number,
                'from_date': from_date
            }

            logger.info(f"Searching bookings for phone: {phone_number}, from_date: {from_date}")

            # Make API request
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully retrieved booking data for {phone_number}")
                logger.info(f"Raw API response: {json.dumps(data, indent=2)}")

                # Check if API response indicates success
                api_status = data.get('status')
                api_status_code = data.get('status_code')

                if api_status == 1 or api_status_code == 'SUCCESS':
                    return {
                        'status': 'success',
                        'data': data,
                        'phone_number': phone_number,
                        'from_date': from_date
                    }
                else:
                    logger.error(f"API returned error status: {api_status}, status_code: {api_status_code}")
                    return {
                        'status': 'error',
                        'message': f'API error: {data.get("message", "Unknown error")}',
                        'phone_number': phone_number,
                        'from_date': from_date
                    }
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {
                    'status': 'error',
                    'message': f'API request failed with status {response.status_code}',
                    'phone_number': phone_number,
                    'from_date': from_date
                }

        except requests.exceptions.Timeout:
            logger.error(f"API request timeout for phone: {phone_number}")
            return {
                'status': 'error',
                'message': 'API request timeout',
                'phone_number': phone_number,
                'from_date': from_date
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error for phone {phone_number}: {e}")
            return {
                'status': 'error',
                'message': f'API request error: {str(e)}',
                'phone_number': phone_number,
                'from_date': from_date
            }
        except Exception as e:
            logger.error(f"Unexpected error searching bookings for {phone_number}: {e}")
            return {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}',
                'phone_number': phone_number,
                'from_date': from_date
            }

    def process_booking_response(self, api_response: Dict) -> List[Dict]:
        """
        Process the API response and extract booking information
        
        Args:
            api_response (Dict): Response from the booking search API
            
        Returns:
            List[Dict]: List of processed booking data
        """
        try:
            if api_response.get('status') != 'success':
                logger.error(f"Cannot process failed API response: {api_response.get('message')}")
                return []

            data = api_response.get('data', {})
            logger.info(f"Processing booking data: {json.dumps(data, indent=2)}")
            bookings = []

            # Handle the actual API response structure
            if isinstance(data, dict):
                # Check if data has a nested 'data' object with 'bookings'
                if 'data' in data and 'bookings' in data['data']:
                    raw_bookings = data['data']['bookings']
                    logger.info(f"Found bookings in nested data structure: {len(raw_bookings)} total bookings")

                    # Filter bookings to exclude inactive statuses
                    filtered_bookings = self._filter_active_bookings(raw_bookings)
                    logger.info(f"After filtering: {len(filtered_bookings)} active bookings")

                    for booking_data in filtered_bookings:
                        bookings.append(self._extract_booking_info(booking_data))

                # If data directly contains bookings
                elif 'bookings' in data:
                    raw_bookings = data['bookings']
                    logger.info(f"Found bookings in direct data structure: {len(raw_bookings)} total bookings")

                    # Filter bookings to exclude inactive statuses
                    filtered_bookings = self._filter_active_bookings(raw_bookings)
                    logger.info(f"After filtering: {len(filtered_bookings)} active bookings")

                    for booking_data in filtered_bookings:
                        bookings.append(self._extract_booking_info(booking_data))

                # If data is a single booking
                elif 'booking_id' in data or 'id' in data:
                    logger.info("Found single booking in data")
                    if self._is_active_booking(data):
                        bookings.append(self._extract_booking_info(data))
                    else:
                        logger.info("Single booking filtered out due to inactive status")

                # If data contains a list of results
                elif 'results' in data:
                    raw_bookings = data['results']
                    logger.info(f"Found bookings in results: {len(raw_bookings)} total bookings")

                    # Filter bookings to exclude inactive statuses
                    filtered_bookings = self._filter_active_bookings(raw_bookings)
                    logger.info(f"After filtering: {len(filtered_bookings)} active bookings")

                    for booking_data in filtered_bookings:
                        bookings.append(self._extract_booking_info(booking_data))

            elif isinstance(data, list):
                # If data is directly a list of bookings
                logger.info(f"Data is a list with {len(data)} total items")

                # Filter bookings to exclude inactive statuses
                filtered_bookings = self._filter_active_bookings(data)
                logger.info(f"After filtering: {len(filtered_bookings)} active bookings")

                for booking_data in filtered_bookings:
                    bookings.append(self._extract_booking_info(booking_data))

            logger.info(f"Processed {len(bookings)} bookings from API response")
            return bookings

        except Exception as e:
            logger.error(f"Error processing booking response: {e}")
            return []

    def _extract_booking_info(self, booking_data: Dict) -> Dict:
        """
        Extract and normalize booking information from API response
        
        Args:
            booking_data (Dict): Raw booking data from API
            
        Returns:
            Dict: Normalized booking information
        """
        try:
            # Extract hotel information from hotel_details
            hotel_details = booking_data.get('hotel_details', {})
            hotel_name = hotel_details.get('hotel_name', 'Unknown Hotel')
            hotel_location = hotel_details.get('legal_address', hotel_details.get('postal_address', 'Unknown Location'))

            # Extract common fields with fallbacks for the actual API structure
            booking_info = {
                'booking_id': booking_data.get('booking_id'),
                'reference_number': booking_data.get('group_code'),  # Using group_code as reference
                'guest_name': booking_data.get('guest_name', 'Guest'),
                'guest_email': booking_data.get('guest_email', ''),
                'guest_phone': booking_data.get('guest_phone', ''),
                'hotel_name': hotel_name,
                'hotel_location': hotel_location,
                'hotel_id': booking_data.get('hotel_code'),
                'check_in_date': self._parse_date_string(booking_data.get('check_in')),
                'check_out_date': self._parse_date_string(booking_data.get('check_out')),
                'booking_status': booking_data.get('status', 'confirmed'),
                'guest_language': booking_data.get('language', 'en'),
                'booking_source': 'treebo_api',
                'total_amount': booking_data.get('total_booking_amount', 0),
                'paid_amount': booking_data.get('paid_amount', 0),
                'balance': booking_data.get('balance', 0),
                'raw_data': booking_data  # Store original data for debugging
            }

            return booking_info

        except Exception as e:
            logger.error(f"Error extracting booking info: {e}")
            return {
                'booking_id': None,
                'raw_data': booking_data,
                'error': str(e)
            }

    def _extract_guest_name(self, booking_data: Dict) -> str:
        """Extract guest name from various possible fields"""
        # Try different field combinations
        if 'guest_name' in booking_data:
            return booking_data['guest_name']
        
        first_name = booking_data.get('first_name', '')
        last_name = booking_data.get('last_name', '')
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()
        
        # Check if there's a customer/guest object
        customers = booking_data.get('customers', [])
        if customers and len(customers) > 0:
            customer = customers[0]
            first_name = customer.get('first_name', '')
            last_name = customer.get('last_name', '')
            return f"{first_name} {last_name}".strip()
        
        return 'Guest'

    def _extract_guest_email(self, booking_data: Dict) -> str:
        """Extract guest email from various possible fields"""
        if 'guest_email' in booking_data:
            return booking_data['guest_email']
        
        if 'email' in booking_data:
            return booking_data['email']
        
        # Check customers array
        customers = booking_data.get('customers', [])
        if customers and len(customers) > 0:
            return customers[0].get('email', '')
        
        return ''

    def _extract_guest_phone(self, booking_data: Dict) -> str:
        """Extract guest phone from various possible fields"""
        if 'guest_phone' in booking_data:
            return booking_data['guest_phone']
        
        if 'phone' in booking_data:
            phone = booking_data['phone']
            if isinstance(phone, dict):
                country_code = phone.get('country_code', '')
                number = phone.get('number', '')
                return f"{country_code}{number}".strip()
            return str(phone)
        
        # Check customers array
        customers = booking_data.get('customers', [])
        if customers and len(customers) > 0:
            phone = customers[0].get('phone', {})
            if isinstance(phone, dict):
                country_code = phone.get('country_code', '')
                number = phone.get('number', '')
                return f"{country_code}{number}".strip()
            return str(phone)
        
        return ''

    def _extract_date(self, booking_data: Dict, field_names: List[str]) -> str:
        """Extract date from various possible field names"""
        for field_name in field_names:
            if field_name in booking_data:
                date_value = booking_data[field_name]
                if date_value:
                    # Try to parse and normalize the date
                    try:
                        if isinstance(date_value, str):
                            # Handle ISO format dates
                            if 'T' in date_value:
                                parsed_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                                return parsed_date.strftime('%Y-%m-%d')
                            else:
                                # Assume it's already in YYYY-MM-DD format
                                return date_value
                        return str(date_value)
                    except Exception as e:
                        logger.warning(f"Could not parse date {date_value}: {e}")
                        return str(date_value)
        return None

    def _parse_date_string(self, date_string: str) -> str:
        """Parse date string from API format to YYYY-MM-DD format"""
        if not date_string:
            return None

        try:
            # API returns dates like "06 June, 2025"
            if ',' in date_string:
                # Parse "06 June, 2025" format
                parsed_date = datetime.strptime(date_string, '%d %B, %Y')
                return parsed_date.strftime('%Y-%m-%d')
            else:
                # If it's already in a standard format, try to parse it
                return date_string
        except Exception as e:
            logger.warning(f"Could not parse date string {date_string}: {e}")
            return date_string

    def _filter_active_bookings(self, bookings_list: List[Dict]) -> List[Dict]:
        """
        Filter bookings to only include active ones (exclude checked_out, cancelled, no_show)

        Args:
            bookings_list (List[Dict]): List of booking data from API

        Returns:
            List[Dict]: Filtered list of active bookings only
        """
        if not bookings_list:
            return []

        active_bookings = []
        inactive_statuses = ['checked_out', 'cancelled', 'no_show', 'canceled']  # Include common variations

        for booking in bookings_list:
            if self._is_active_booking(booking):
                active_bookings.append(booking)
            else:
                booking_id = booking.get('booking_id', 'Unknown')
                status = booking.get('status', 'Unknown')
                logger.info(f"Filtering out booking {booking_id} with status: {status}")

        return active_bookings

    def _is_active_booking(self, booking_data: Dict) -> bool:
        """
        Check if a booking is active (should be shown to user)

        Args:
            booking_data (Dict): Single booking data from API

        Returns:
            bool: True if booking is active, False if it should be filtered out
        """
        status = booking_data.get('status', '').lower().strip()

        # List of statuses that should be filtered out
        inactive_statuses = [
            'checked_out',
            'cancelled',
            'canceled',  # Alternative spelling
            'no_show',
            'no-show',
            'noshow'
        ]

        # Check if status is in the inactive list
        is_inactive = status in inactive_statuses

        if is_inactive:
            booking_id = booking_data.get('booking_id', 'Unknown')
            logger.info(f"Booking {booking_id} has inactive status '{status}' - will be filtered out")
            return False

        # Additional checks can be added here if needed
        # For example, check dates, payment status, etc.

        return True
