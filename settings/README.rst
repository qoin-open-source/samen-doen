Using these settings
====================

Set the environment variable `DJANGO_SETTINGS_MODULE` to point to the correct module. This will typically be done by editing the virtualenv activate script to include something like this:

    export DJANGO_SETTINGS_MODULE='icare4u_front.settings.local'


Sensitive settings
------------------

Servers
~~~~~~~

For production and staging environments this is done through Yaybu.

Development
~~~~~~~~~~~

Copy `secret.py.template` to `secret.py`, e.g.:

    cp icare4u_front/settings/secret.py.template icare4u_front/settings/secret.py

Add your settings to `secret.py` and keep `DJANGO_SETTINGS_MODULE` pointing at `icare4u_front.settings.local`.
