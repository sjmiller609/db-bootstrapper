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
        'kubernetes==8.0.0',
        'urllib3==1.23',
    ],
    entry_points={
        'console_scripts': [
            'db-bootstrapper=main:main'
        ]
    }
)
