from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='sci-figure',
    version='0.1.0',
    description='Scientific figure extractor for academic PDF papers',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='ShClaw',
    url='https://github.com/xssjqx/Sh_Sci_Fig',
    license='AGPL-3.0-or-later',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'pdfplumber>=0.10.0',
        'PyMuPDF>=1.24.0',
        'opencv-python>=4.9.0',
        'Pillow>=10.0.0',
        'pytesseract>=0.3.10',
        'numpy>=1.24.0',
    ],
    entry_points={
        'console_scripts': [
            'sh-sci-fig=src.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Scientific/Engineering',
    ],
)
