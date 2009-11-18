from setuptools import setup

setup(
    name='babbisch-ooc',
    version='0.1',
    packages=['babbisch_ooc', 'babbisch_ooc.wraplib'],

    entry_points={
            'console_scripts': [
                'babbisch-ooc = babbisch_ooc:main',
            ]
    }
)
