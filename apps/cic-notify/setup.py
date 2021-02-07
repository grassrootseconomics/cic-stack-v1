# standard imports
from setuptools import setup

# third-party imports

# local imports


requirements = []
requirements_file = open('requirements.txt', 'r')
while True:
    requirement = requirements_file.readline()
    if requirement == '':
        break
    requirements.append(requirement.rstrip())
requirements_file.close()

test_requirements = []
test_requirements_file = open('test_requirements.txt', 'r')
while True:
    test_requirement = test_requirements_file.readline()
    if test_requirement == '':
        break
    test_requirements.append(test_requirement.rstrip())
test_requirements_file.close()

setup(
    install_requires=requirements,
    tests_require=test_requirements,
)
