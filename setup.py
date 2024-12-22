from setuptools import setup, find_packages

setup(
    name="mclemore-auction-tools",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'requests',
        'python-dotenv',
        'lob',
        'pandas',
        'pytest'
    ],
)
