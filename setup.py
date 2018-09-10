from setuptools import find_packages, setup

setup(
    name="requests_spider",
    version="0.0.5",
    description="Web crawling framework like flask.",
    author="Tommy",
    long_description=open('README.md').read(),
    author_email="tooooommy@163.com",
    url='https://github.com/Tooooomy/requests_spider',
    python_requires='>=3.6.0',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    install_requires=[
        'requests-html'
    ],
    license='MIT',
    packages=find_packages(),
    py_modules=['requests_spider'],
    platforms=["all"],
    include_package_data=True,
    zip_safe=False
)