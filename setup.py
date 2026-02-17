from setuptools import setup, find_packages

setup(
    name="adtool",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "ldap3"
    ],
    entry_points={
        "console_scripts": [
            "adtool=adtool.cli:main"
        ]
    },
)
