"""
Setup configuration for Masjid Connect Backend API.

This setup.py is specifically designed for Azure App Service ORYX deployment.
It ensures that:
1. The 'src' package is properly installed and discoverable
2. All dependencies are installed correctly
3. The application can find all modules at runtime
"""

from setuptools import setup, find_packages
import os


def read_requirements():
    """Read requirements from requirements.txt file."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r', encoding='utf-8') as f:
        # Filter out comments and empty lines
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]
    return requirements


def read_readme():
    """Read README for long description."""
    readme_path = os.path.join(os.path.dirname(__file__), 'docs', 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Masjid Connect Backend API"


setup(
    name="masjidconnect-backend",
    version="1.0.0",
    description="Masjid Connect API Service - FastAPI backend with Azure SQL support",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Development Team",
    author_email="baigmm1@gmail.com",
    license="MIT",
    python_requires=">=3.11",
    
    # Package discovery - critical for ORYX deployment
    packages=find_packages(where='.', include=['src', 'src.*']),
    package_dir={'': '.'},
    
    # Include package data
    include_package_data=True,
    package_data={
        'src': ['py.typed'],
    },
    
    # Dependencies from requirements.txt
    install_requires=read_requirements(),
    
    # Entry points for console scripts (optional but recommended)
    entry_points={
        'console_scripts': [
            'masjidconnect-api=src.main:app',
        ],
    },
    
    # Additional metadata
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Framework :: FastAPI',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    
    # Project URLs
    project_urls={
        'Source': 'https://github.com/baigmm1/mmc-application',
    },
    
    # Zip safe
    zip_safe=False,
)
