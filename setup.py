from setuptools import setup, find_packages

setup(
    name='db_bootstrapper',
    version='0.0.1',
    py_modules=['main'],
    install_requires=[
        'click==6.7',
        'psycopg2==2.7.5',
        'SQLAlchemy==1.2.9',
        'sqlalchemy-utils==0.33.0',
        'kubernetes==7.0.0',
    ],
    entry_points={
        'console_scripts': [
            'db-bootstrapper=main:main'
        ]
    }
)
