import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="ocsf_transformation",
    version="0.1.0",
    
    description="CDK app for OCSF transformation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    author="Amazon",
    
    package_dir={"": "ocsf_transformation"},
    packages=setuptools.find_packages(where="ocsf_transformation"),
    
    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
    
    python_requires=">=3.8",
)
