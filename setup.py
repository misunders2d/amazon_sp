from setuptools import find_packages, setup

setup(
    name="amazon sp api modules",  # Name of your package
    version="0.1.0",  # Version number
    description="modules for Amazon SP API interactions",
    author="Sergey",
    author_email="2djohar@gmail.com",
    packages=find_packages(),  # Automatically find all packages
    install_requires=[],
    python_requires=">=3.6",  # Specify compatible Python versions
)
