from setuptools import setup, find_packages

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.read().strip().split()

setup(
    name='db_bootstrapper',
    version='0.0.2',
    py_modules=['main'],
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'db-bootstrapper=main:main'
        ]
    }
)
