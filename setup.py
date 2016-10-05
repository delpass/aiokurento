# import os
from setuptools import setup

setup(
    name="aiokurento",
    version="0.1.0",
    author="Yaroslav Sazonov",
    author_email="delpass@gmail.com",
    description="KMS driver for AsyncIO",
    license="MIT",
    keywords="kms kurento aio asyncio ",
    url="http://packages.python.org/aiokurento",
    packages=['kurento'],
    long_description=open('README.md').read(),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        #'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=['aiohttp']
)
