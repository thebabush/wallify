# Wallify

Simple python script to put together a nice wallpaper from your Spotify music.

## Requirements

* Linux
* KDE 5 (it's easy to add support for other DEs...)
* DBUS and friends
* A bunch of python packages that I still have to put in a `requirements.txt`

## Install

```sh
virtualenv --system-site-packages -p /usr/bin/python3 /path/to/venv
source /path/to/venv/bin/activate

git clone git@github.com:kenoph/wallify.git
cd wallify

pip install -r requirements.txt --upgrade
# If you get errors in OpenSSL.SSL, do `easy_install pyopenssl`

# Get the keys from https://developer.spotify.com/my-applications/ and save them to cred.txt
echo <client id> >> creds.txt
echo <client secret> >> creds.txt

./wallify.py
```

## Screenshot

![Screenshot](https://user-images.githubusercontent.com/1985669/38062202-93d91e60-32a7-11e8-97b7-fdb9ccb77172.jpg)

