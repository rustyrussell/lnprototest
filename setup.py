from setuptools import setup
import io


with io.open('README.md', encoding='utf-8') as f:
    long_description = f.read()

with io.open('requirements.txt', encoding='utf-8') as f:
    requirements = [r for r in f.read().split('\n') if len(r)]

setup(name='lnprototest',
      version='0.0.1',
      description='Spec protocol tests for lightning network implementations',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Rusty Russell',
      author_email='rusty@ln.dev',
      license='MIT',
      packages=['lnprototest', 'lnprototest.clightning'],
      scripts=[],
      zip_safe=True,
      install_requires=requirements)
