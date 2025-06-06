import logging
from typing import Dict, Optional, List
from chatbot.models import User
from config.database import db

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user authentication and sessions"""

    def __init__(self):
        pass

    def create_or_get_user(self, phone_number: str, name: str = None, email: str = None) -> Dict:
        """
        Create a new user or get existing user by phone number
        
        Args:
            phone_number (str): User's phone number
            name (str, optional): User's name
            email (str, optional): User's email
            
        Returns:
            Dict: User information with session token
        """
        try:
            # Clean phone number (remove spaces, dashes, etc.)
            clean_phone = self._clean_phone_number(phone_number)
            
            # Check if user already exists
            user = User.query.filter_by(phone_number=clean_phone).first()
            
            if user:
                # Update user info if provided
                if name and name != user.name:
                    user.name = name
                if email and email != user.email:
                    user.email = email
                
                # Generate new session token
                user.generate_session_token()
                user.is_active = True
                
                db.session.commit()
                
                logger.info(f"Updated existing user session for phone: {clean_phone}")
                
                return {
                    'status': 'success',
                    'user': user.to_dict(),
                    'session_token': user.session_token,
                    'is_new_user': False
                }
            else:
                # Create new user
                user = User(
                    phone_number=clean_phone,
                    name=name or 'User',
                    email=email,
                    is_active=True
                )
                user.generate_session_token()
                
                db.session.add(user)
                db.session.commit()
                
                logger.info(f"Created new user for phone: {clean_phone}")
                
                return {
                    'status': 'success',
                    'user': user.to_dict(),
                    'session_token': user.session_token,
                    'is_new_user': True
                }

        except Exception as e:
            logger.error(f"Error creating/getting user for phone {phone_number}: {e}")
            db.session.rollback()
            return {
                'status': 'error',
                'message': f'Error managing user: {str(e)}'
            }

    def get_user_by_token(self, session_token: str) -> Optional[User]:
        """
        Get user by session token
        
        Args:
            session_token (str): User's session token
            
        Returns:
            User: User object if found and active, None otherwise
        """
        try:
            user = User.query.filter_by(
                session_token=session_token,
                is_active=True
            ).first()
            
            if user:
                logger.debug(f"Found active user for token: {session_token[:8]}...")
                return user
            else:
                logger.warning(f"No active user found for token: {session_token[:8]}...")
                return None

        except Exception as e:
            logger.error(f"Error getting user by token: {e}")
            return None

    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Get user by phone number
        
        Args:
            phone_number (str): User's phone number
            
        Returns:
            User: User object if found, None otherwise
        """
        try:
            clean_phone = self._clean_phone_number(phone_number)
            user = User.query.filter_by(phone_number=clean_phone).first()
            
            if user:
                logger.debug(f"Found user for phone: {clean_phone}")
                return user
            else:
                logger.debug(f"No user found for phone: {clean_phone}")
                return None

        except Exception as e:
            logger.error(f"Error getting user by phone {phone_number}: {e}")
            return None

    def validate_session(self, session_token: str) -> Dict:
        """
        Validate user session token
        
        Args:
            session_token (str): Session token to validate
            
        Returns:
            Dict: Validation result with user info if valid
        """
        try:
            user = self.get_user_by_token(session_token)
            
            if user:
                return {
                    'status': 'valid',
                    'user': user.to_dict(),
                    'phone_number': user.phone_number
                }
            else:
                return {
                    'status': 'invalid',
                    'message': 'Invalid or expired session token'
                }

        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return {
                'status': 'error',
                'message': f'Error validating session: {str(e)}'
            }

    def logout_user(self, session_token: str) -> Dict:
        """
        Logout user by invalidating session token
        
        Args:
            session_token (str): Session token to invalidate
            
        Returns:
            Dict: Logout result
        """
        try:
            user = self.get_user_by_token(session_token)
            
            if user:
                user.session_token = None
                user.is_active = False
                db.session.commit()
                
                logger.info(f"Logged out user: {user.phone_number}")
                
                return {
                    'status': 'success',
                    'message': 'User logged out successfully'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Invalid session token'
                }

        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            db.session.rollback()
            return {
                'status': 'error',
                'message': f'Error logging out: {str(e)}'
            }

    def _clean_phone_number(self, phone_number: str) -> str:
        """
        Clean and normalize phone number
        
        Args:
            phone_number (str): Raw phone number
            
        Returns:
            str: Cleaned phone number
        """
        if not phone_number:
            return ''
        
        # Remove common separators and spaces
        cleaned = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        
        # Remove any non-digit characters except +
        cleaned = ''.join(char for char in cleaned if char.isdigit())
        
        return cleaned

    def get_all_users(self, limit: int = 50) -> List[Dict]:
        """
        Get all users (for admin purposes)
        
        Args:
            limit (int): Maximum number of users to return
            
        Returns:
            List[Dict]: List of user information
        """
        try:
            users = User.query.order_by(User.created_at.desc()).limit(limit).all()
            
            return [user.to_dict() for user in users]

        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def update_user(self, session_token: str, name: str = None, email: str = None) -> Dict:
        """
        Update user information
        
        Args:
            session_token (str): User's session token
            name (str, optional): New name
            email (str, optional): New email
            
        Returns:
            Dict: Update result
        """
        try:
            user = self.get_user_by_token(session_token)
            
            if not user:
                return {
                    'status': 'error',
                    'message': 'Invalid session token'
                }
            
            # Update provided fields
            if name is not None:
                user.name = name
            if email is not None:
                user.email = email
            
            db.session.commit()
            
            logger.info(f"Updated user info for: {user.phone_number}")
            
            return {
                'status': 'success',
                'user': user.to_dict(),
                'message': 'User updated successfully'
            }

        except Exception as e:
            logger.error(f"Error updating user: {e}")
            db.session.rollback()
            return {
                'status': 'error',
                'message': f'Error updating user: {str(e)}'
            }
