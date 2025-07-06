#!/usr/bin/env python
"""Setup script for Vanna MCP Server."""

from setuptools import setup, find_packages
import os

# Read the README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="vanna-mcp-server",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="MCP server for natural language to SQL conversion with multi-tenant support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/vanna-mcp-server",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vanna-mcp-server=server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/vanna-mcp-server/issues",
        "Source": "https://github.com/yourusername/vanna-mcp-server",
        "Documentation": "https://github.com/yourusername/vanna-mcp-server/tree/main/docs",
    },
)