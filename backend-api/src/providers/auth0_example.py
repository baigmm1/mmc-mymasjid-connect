"""
Auth0 Provider Usage Example

Demonstrates how to use the Auth0Provider to fetch user information.
"""

import asyncio
from src.providers.auth0_provider import get_auth0_provider


async def example_get_user_info():
    """Example: Fetch complete user info from Auth0"""
    
    # Access token would typically come from the Authorization header
    # This is just a placeholder - use actual token in production
    access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    # Create Auth0 provider instance
    auth0_provider = get_auth0_provider()
    
    try:
        # Fetch full user information
        user_info = await auth0_provider.get_user_info(access_token)
        
        print("Full User Info:")
        print(f"User ID: {user_info.get('sub')}")
        print(f"Email: {user_info.get('email')}")
        print(f"Name: {user_info.get('name')}")
        print(f"Email Verified: {user_info.get('email_verified')}")
        print(f"Picture: {user_info.get('picture')}")
        print(f"Updated At: {user_info.get('updated_at')}")
        
        # Handle custom claims (if configured in Auth0)
        # Custom claims are typically namespaced
        roles = user_info.get('https://masjidconnect.auth0.com/roles', [])
        print(f"Roles: {roles}")
        
    except Exception as e:
        print(f"Error fetching user info: {str(e)}")


async def example_get_user_profile():
    """Example: Fetch simplified user profile"""
    
    access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    auth0_provider = get_auth0_provider()
    
    try:
        # Fetch basic profile information
        profile = await auth0_provider.get_user_profile(access_token)
        
        print("\nUser Profile:")
        print(f"User ID: {profile['user_id']}")
        print(f"Email: {profile['email']}")
        print(f"Name: {profile['name']}")
        print(f"Email Verified: {profile['email_verified']}")
        
    except Exception as e:
        print(f"Error fetching user profile: {str(e)}")


async def example_get_user_email():
    """Example: Fetch only user email"""
    
    access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    auth0_provider = get_auth0_provider()
    
    try:
        # Fetch just the email
        email = await auth0_provider.get_user_email(access_token)
        print(f"\nUser Email: {email}")
        
    except Exception as e:
        print(f"Error fetching user email: {str(e)}")


async def example_integration_with_jwt():
    """Example: Using Auth0Provider with JWT token from request"""
    
    # Simulating FastAPI dependency injection scenario
    # In real application, token comes from Authorization header
    
    from fastapi import Header, HTTPException, status
    
    async def get_current_user_from_auth0(
        authorization: str = Header(None)
    ):
        """Dependency that fetches user info from Auth0"""
        
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing"
            )
        
        # Extract token from "Bearer <token>" format
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        # Fetch user info from Auth0
        auth0_provider = get_auth0_provider()
        try:
            user_info = await auth0_provider.get_user_info(token)
            return user_info
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to fetch user info: {str(e)}"
            )
    
    print("\nIntegration example defined - use in FastAPI routes as dependency")


async def main():
    """Run all examples"""
    print("Auth0 Provider Usage Examples")
    print("=" * 50)
    
    # Note: These examples will fail without a valid token
    # Uncomment when you have a real access token
    
    # await example_get_user_info()
    # await example_get_user_profile()
    # await example_get_user_email()
    await example_integration_with_jwt()
    
    print("\n" + "=" * 50)
    print("Examples completed")


if __name__ == "__main__":
    asyncio.run(main())
