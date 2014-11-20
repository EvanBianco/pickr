pickr
=====

Web-app for collaborative image interpretation.

## Development Environment

Requires Google App Engine and Python

### [pip](https://github.com/pypa/pip) Python Package Manager

    sudo easy_install pip

### Python Image Library

    sudo pip install PIL --allow-external PIL --allow-unverified PIL
    
See <http://stackoverflow.com/a/21243133/483776>
    

## Local Testing

    dev_appserver.py . --clear_datastore true --log_level debug

For Remote Access

    dev_appserver.py . --clear_datastore true --log_level debug --host 0.0.0.0
