#!/bin/bash
# Set up virtualenv and migrate project
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/media_management_api -r /home/vagrant/media_management_api/media_management_api/requirements/local.txt media_management_api 
workon media_management_api
python manage.py migrate
