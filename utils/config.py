#!/usr/bin/env python3
"""
Configuration Management

Loads Azure OpenAI credentials from environment variables.
Never commit .env file to GitHub!
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


def get_azure_config() -> dict:
    """
    Get Azure OpenAI configuration from environment variables
    
    Returns:
        dict with keys: endpoint, api_key, deployment
        
    Raises:
        ValueError if required environment variables are not set
    """
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-5-mini')
    
    if not endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT not set. "
            "Copy env.example to .env and fill in your credentials."
        )
    
    if not api_key:
        raise ValueError(
            "AZURE_OPENAI_API_KEY not set. "
            "Copy env.example to .env and fill in your credentials."
        )
    
    return {
        'endpoint': endpoint,
        'api_key': api_key,
        'deployment': deployment
    }


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default"""
    return os.getenv(key, default)


def check_config() -> bool:
    """
    Check if configuration is properly set up
    
    Returns:
        True if all required variables are set, False otherwise
    """
    try:
        config = get_azure_config()
        print("OK - Configuration loaded successfully")
        print(f"  Endpoint: {config['endpoint']}")
        print(f"  Deployment: {config['deployment']}")
        print(f"  API Key: {config['api_key'][:10]}...{config['api_key'][-5:]}")
        return True
    except ValueError as e:
        print(f"ERROR - Configuration error: {e}")
        print("\nSetup instructions:")
        print("1. Copy env.example to .env")
        print("2. Edit .env and add your Azure OpenAI credentials")
        print("3. Run this script again")
        return False


if __name__ == '__main__':
    print("=" * 80)
    print("Configuration Check")
    print("=" * 80)
    print()
    check_config()
