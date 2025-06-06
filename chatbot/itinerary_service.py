import logging
import openai
from datetime import datetime
from typing import Dict
import os

logger = logging.getLogger(__name__)


class ItineraryService:
    """Service for generating AI-powered travel itineraries using OpenAI"""

    def __init__(self):
        """Initialize the itinerary service with OpenAI configuration"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found. Itinerary generation will not work.")
            return

        # Remove quotes if present
        self.openai_api_key = self.openai_api_key.strip("'\"")
        logger.info(f"OpenAI API key loaded: {self.openai_api_key[:10]}...{self.openai_api_key[-4:]}")

        # Set OpenAI API key
        openai.api_key = self.openai_api_key

        # Configuration
        self.model = "gpt-4"  # Use GPT-4 for best results
        self.max_tokens = 2000
        self.temperature = 0.7

        logger.info("ItineraryService initialized successfully")

    def calculate_stay_duration(self, check_in_date: str, check_out_date: str) -> Dict:
        """
        Calculate the duration of stay and return useful information

        Args:
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format

        Returns:
            Dict containing duration info
        """
        try:
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d')

            duration = check_out - check_in
            nights = duration.days

            # Determine trip type based on duration
            if nights == 1:
                trip_type = "short_stay"
                trip_description = "1-night short stay"
            elif nights <= 3:
                trip_type = "weekend_getaway"
                trip_description = f"{nights}-night weekend getaway"
            elif nights <= 7:
                trip_type = "week_vacation"
                trip_description = f"{nights}-night vacation"
            else:
                trip_type = "extended_stay"
                trip_description = f"{nights}-night extended stay"

            return {
                'nights': nights,
                'days': nights + 1,  # Days include check-out day
                'trip_type': trip_type,
                'trip_description': trip_description,
                'check_in_formatted': check_in.strftime('%B %d, %Y'),
                'check_out_formatted': check_out.strftime('%B %d, %Y'),
                'day_of_week_checkin': check_in.strftime('%A'),
                'day_of_week_checkout': check_out.strftime('%A')
            }

        except Exception as e:
            logger.error(f"Error calculating stay duration: {e}")
            return {
                'nights': 1,
                'days': 2,
                'trip_type': 'short_stay',
                'trip_description': '1-night stay',
                'check_in_formatted': check_in_date,
                'check_out_formatted': check_out_date,
                'day_of_week_checkin': 'Unknown',
                'day_of_week_checkout': 'Unknown'
            }

    def extract_city_from_location(self, hotel_location: str) -> str:
        """
        Simple city extraction - just return the hotel location as-is
        Let OpenAI figure out the city from the location string

        Args:
            hotel_location: Full hotel location string

        Returns:
            Hotel location (OpenAI will extract city from this)
        """
        return hotel_location.strip() if hotel_location else "Unknown Location"

    def generate_itinerary_prompt(self, booking_data: Dict, duration_info: Dict, hotel_location: str, language: str = 'en') -> str:
        """
        Generate a comprehensive prompt for OpenAI to create the itinerary

        Args:
            booking_data: Booking information
            duration_info: Stay duration information
            hotel_location: Hotel location string (OpenAI will determine city)
            language: Language code for the response (en, hi, etc.)

        Returns:
            Formatted prompt string
        """
        # Language mapping
        language_instructions = {
            'en': 'Respond in English',
            'hi': 'Respond in Hindi (हिंदी में जवाब दें)',
            'es': 'Respond in Spanish',
            'ta': 'Respond in Tamil',
            'te': 'Respond in Telugu',
            'bn': 'Respond in Bengali',
            'mr': 'Respond in Marathi',
            'gu': 'Respond in Gujarati',
            'kn': 'Respond in Kannada',
            'ml': 'Respond in Malayalam',
            'pa': 'Respond in Punjabi'
        }

        lang_instruction = language_instructions.get(language, 'Respond in English')

        prompt = f"""Create a detailed and personalized travel itinerary for a {duration_info['trip_description']} based on the hotel location: {hotel_location}

LANGUAGE REQUIREMENT: {lang_instruction}

First, identify the city/destination from the hotel location, then create the itinerary for that destination.

BOOKING DETAILS:
- Hotel: {booking_data.get('hotel_name', 'N/A')}
- Hotel Location: {hotel_location}
- Check-in: {duration_info['check_in_formatted']} ({duration_info['day_of_week_checkin']})
- Check-out: {duration_info['check_out_formatted']} ({duration_info['day_of_week_checkout']})
- Duration: {duration_info['nights']} nights, {duration_info['days']} days
- Guest: {booking_data.get('guest_name', 'Traveler')}

REQUIREMENTS:
1. Create a day-by-day itinerary for {duration_info['days']} days
2. Include specific timings for each activity
3. Suggest restaurants for breakfast, lunch, and dinner
4. Include must-visit tourist attractions
5. Add shopping recommendations
6. Suggest local experiences and cultural activities
7. Include transportation tips
8. Add practical tips and suggestions
9. Consider the day of the week for opening hours
10. Include approximate costs in INR where relevant

FORMAT:
Use this exact structure without any markdown formatting (no ** or other markdown):

🗓️ ITINERARY FOR [CITY NAME] (determine city from hotel location)
📅 {duration_info['check_in_formatted']} to {duration_info['check_out_formatted']}

DAY 1 - {duration_info['day_of_week_checkin']} ({duration_info['check_in_formatted']})

🌅 Morning (9:00 AM - 12:00 PM)
• Activity details with specific timings and locations
• Restaurant suggestions with cuisine type and approximate costs

🌞 Afternoon (12:00 PM - 5:00 PM)
• Activity details with specific timings and locations
• Lunch recommendations with costs

🌆 Evening (5:00 PM - 9:00 PM)
• Activity details with specific timings and locations
• Dinner suggestions with costs

[Continue for each day...]

💡 TRAVEL TIPS & SUGGESTIONS

🚗 Transportation:
• Local transport options and costs
• Booking apps and services

🍽️ Food Recommendations:
• Must-try local dishes
• Popular restaurants and cafes

🛍️ Shopping:
• Best markets and malls
• Local specialties to buy

💰 Budget Tips:
• Estimated daily costs
• Money-saving suggestions

🎯 Local Experiences:
• Cultural activities
• Hidden gems and local favorites

⚠️ Important Notes:
• Weather considerations
• Safety tips
• Best times to visit attractions

Make it engaging, practical, and tailored to the specific duration and city. Include specific place names, addresses where helpful, and realistic timings.

IMPORTANT: Do not use any markdown formatting like ** or * in your response. Use plain text with emojis and bullet points (•) only."""

        return prompt

    def generate_itinerary(self, booking_data: Dict, language: str = 'en') -> Dict:
        """
        Generate a complete travel itinerary using OpenAI

        Args:
            booking_data: Complete booking information
            language: Language code for the response (en, hi, etc.)

        Returns:
            Dict containing the generated itinerary or error information
        """
        try:
            # Extract required information
            check_in_date = booking_data.get('check_in_date', booking_data.get('check_in'))
            check_out_date = booking_data.get('check_out_date', booking_data.get('check_out'))
            hotel_location = booking_data.get('hotel_location', '')

            if not check_in_date or not check_out_date:
                return {
                    'success': False,
                    'error': 'Missing check-in or check-out dates',
                    'message': 'Unable to generate itinerary without complete booking dates.'
                }

            # Calculate stay duration
            duration_info = self.calculate_stay_duration(check_in_date, check_out_date)

            # Use hotel location directly (let OpenAI figure out the city)
            location_display = self.extract_city_from_location(hotel_location)

            logger.info(f"Generating itinerary for location: {location_display}, {duration_info['nights']} nights")

            # Check if OpenAI API key is available and valid
            if (not self.openai_api_key or
                    self.openai_api_key == 'your_openai_api_key_here' or
                    len(self.openai_api_key.strip()) < 10):
                logger.warning("OpenAI API key not configured or invalid")
                return {
                    'success': False,
                    'error': 'OpenAI API key not configured',
                    'message': 'Not able to generate itinerary at the moment.'
                }

            logger.info(f"Using OpenAI API for itinerary generation (key: {self.openai_api_key[:10]}...)")

            # Generate prompt for real OpenAI API
            prompt = self.generate_itinerary_prompt(booking_data, duration_info, hotel_location, language)

            logger.info(f"Generating itinerary for {hotel_location}, {duration_info['nights']} nights")

            # Language-specific system message
            language_names = {
                'en': 'English',
                'hi': 'Hindi',
                'es': 'Spanish',
                'ta': 'Tamil',
                'te': 'Telugu',
                'bn': 'Bengali',
                'mr': 'Marathi',
                'gu': 'Gujarati',
                'kn': 'Kannada',
                'ml': 'Malayalam',
                'pa': 'Punjabi'
            }

            lang_name = language_names.get(language, 'English')
            system_message = f"You are an expert travel planner specializing in Indian destinations. Create detailed, practical, and engaging travel itineraries with specific recommendations, timings, and local insights. Respond in {lang_name} language."

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            # Extract the generated itinerary
            itinerary_text = response.choices[0].message.content.strip()

            logger.info(f"Successfully generated itinerary for {location_display} ({len(itinerary_text)} characters)")

            return {
                'success': True,
                'itinerary': itinerary_text,
                'location': location_display,
                'duration_info': duration_info,
                'booking_data': booking_data,
                'tokens_used': response.usage.total_tokens,
                'model_used': self.model
            }

        except openai.error.AuthenticationError:
            logger.error("OpenAI authentication failed")
            return {
                'success': False,
                'error': 'OpenAI authentication failed',
                'message': 'Not able to generate itinerary at the moment.'
            }
        except openai.error.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return {
                'success': False,
                'error': 'Rate limit exceeded',
                'message': 'Not able to generate itinerary at the moment.'
            }
        except openai.error.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                'success': False,
                'error': f'OpenAI API error: {e}',
                'message': 'Not able to generate itinerary at the moment.'
            }
        except Exception as e:
            logger.error(f"Error generating itinerary: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Not able to generate itinerary at the moment.'
            }

    def format_itinerary_for_chat(self, itinerary_result: Dict) -> str:
        """
        Format the generated itinerary for chat display

        Args:
            itinerary_result: Result from generate_itinerary

        Returns:
            Formatted message string
        """
        if not itinerary_result.get('success'):
            return f"❌ {itinerary_result.get('message', 'Failed to generate itinerary')}"

        itinerary = itinerary_result.get('itinerary', '')
        duration_info = itinerary_result.get('duration_info', {})

        # Extract city name from the itinerary content
        city_name = "Your Destination"
        if "ITINERARY FOR" in itinerary:
            try:
                city_line = [line for line in itinerary.split('\n') if 'ITINERARY FOR' in line][0]
                city_name = city_line.split('ITINERARY FOR')[1].strip()
            except:
                pass

        # Create clean header without markdown
        header = f"🎯 PERSONALIZED TRAVEL ITINERARY\n\n"
        header += f"📍 Destination: {city_name}\n"
        header += f"⏱️ Duration: {duration_info.get('trip_description', 'N/A')}\n"
        header += f"🤖 Generated by AI\n\n"

        # Clean up the itinerary content - remove any remaining markdown
        clean_itinerary = itinerary.replace('**', '').replace('*', '')

        # Add the main itinerary
        formatted_message = header + clean_itinerary

        # Add footer
        footer = f"\n\n💡 Need Changes?\n"
        footer += f"This itinerary is AI-generated and can be customized based on your preferences.\n\n"
        footer += f"🔙 Type 'back' to return to recommendations menu."

        return formatted_message + footer

