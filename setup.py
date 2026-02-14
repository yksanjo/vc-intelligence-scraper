#!/usr/bin/env python3
"""
VC Intelligence Scraper
SEC EDGAR scraper package for VCs, family offices, and institutional investors
"""

from setuptools import setup, find_packages

setup(
    name="vc-intelligence-scraper",
    version="1.0.0",
    description="SEC EDGAR scraper for investor intelligence",
    author="Yoshi Tomioka",
    author_email="yoshi@example.com",
    url="https://github.com/yksanjo/vc-intelligence-scraper",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "pandas>=1.5.0",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "vc-scrape=sec_scraper:main",
        ],
    },
)
