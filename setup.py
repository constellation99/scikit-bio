#!/usr/bin/env python

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

import os
import platform
import re
import ast
from setuptools import find_packages, setup
from setuptools.extension import Extension
from setuptools.command.build_ext import build_ext as _build_ext


# Bootstrap setup.py with numpy
# Huge thanks to coldfix's solution
# http://stackoverflow.com/a/21621689/579416
class build_ext(_build_ext):
    def finalize_options(self):
        _build_ext.finalize_options(self)
        # Prevent numpy from thinking it is still in its setup process:
        __builtins__.__NUMPY_SETUP__ = False
        import numpy
        self.include_dirs.append(numpy.get_include())

# version parsing from __init__ pulled from Flask's setup.py
# https://github.com/mitsuhiko/flask/blob/master/setup.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('skbio/__init__.py', 'rb') as f:
    hit = _version_re.search(f.read().decode('utf-8')).group(1)
    version = str(ast.literal_eval(hit))

classes = """
    Development Status :: 4 - Beta
    License :: OSI Approved :: BSD License
    Topic :: Software Development :: Libraries
    Topic :: Scientific/Engineering
    Topic :: Scientific/Engineering :: Bio-Informatics
    Programming Language :: Python
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3 :: Only
    Programming Language :: Python :: 3.4
    Programming Language :: Python :: 3.5
    Operating System :: Unix
    Operating System :: POSIX
    Operating System :: MacOS :: MacOS X
"""
classifiers = [s.strip() for s in classes.split('\n') if s]

description = ('Data structures, algorithms and educational '
               'resources for bioinformatics.')

with open('README.rst') as f:
    long_description = f.read()

# Dealing with Cython
USE_CYTHON = os.environ.get('USE_CYTHON', False)
ext = '.pyx' if USE_CYTHON else '.c'

# There's a bug in some versions of Python 3.4 that propagates
# -Werror=declaration-after-statement to extensions, instead of just affecting
# the compilation of the interpreter. See http://bugs.python.org/issue21121 for
# details. This acts as a workaround until the next Python 3 release -- thanks
# Wolfgang Maier (wolma) for the workaround!
ssw_extra_compile_args = ['-Wno-error=declaration-after-statement']

# Users with i686 architectures have reported that adding this flag allows
# SSW to be compiled. See https://github.com/biocore/scikit-bio/issues/409 and
# http://stackoverflow.com/q/26211814/3776794 for details.
if platform.machine() == 'i686':
    ssw_extra_compile_args.append('-msse2')

extensions = [
    Extension("skbio.stats.__subsample",
              ["skbio/stats/__subsample" + ext]),
    Extension("skbio.alignment._ssw_wrapper",
              ["skbio/alignment/_ssw_wrapper" + ext,
               "skbio/alignment/_lib/ssw.c"],
              extra_compile_args=ssw_extra_compile_args),
    Extension("skbio.diversity._phylogenetic",
              ["skbio/diversity/_phylogenetic" + ext])
]

if USE_CYTHON:
    from Cython.Build import cythonize
    extensions = cythonize(extensions)

setup(name='scikit-bio',
      version=version,
      license='BSD',
      description=description,
      long_description=long_description,
      author="scikit-bio development team",
      author_email="gregcaporaso@gmail.com",
      maintainer="scikit-bio development team",
      maintainer_email="gregcaporaso@gmail.com",
      url='http://scikit-bio.org',
      packages=find_packages(),
      ext_modules=extensions,
      cmdclass={'build_ext': build_ext},
      setup_requires=['numpy >= 1.9.2'],
      install_requires=[
          'bz2file >= 0.98',
          'lockfile >= 0.10.2',
          'CacheControl >= 0.11.5',
          'decorator >= 3.4.2',
          'IPython >= 3.2.0',
          'matplotlib >= 1.4.3',
          'natsort >= 4.0.3',
          'numpy >= 1.9.2',
          'pandas >= 0.17.0',
          'scipy >= 0.15.1',
          'nose >= 1.3.7'
      ],
      classifiers=classifiers,
      package_data={
          'skbio.diversity.alpha.tests': ['data/qiime-191-tt/*'],
          'skbio.diversity.beta.tests': ['data/qiime-191-tt/*'],
          'skbio.io.tests': ['data/*'],
          'skbio.io.format.tests': ['data/*'],
          'skbio.stats.tests': ['data/*'],
          'skbio.stats.distance.tests': ['data/*'],
          'skbio.stats.ordination.tests': ['data/*']
          }
      )
