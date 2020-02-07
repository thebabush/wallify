#!/usr/bin/env python3

import hashlib
import os
import urllib
import random
import shutil

import PIL.Image
import pydbus
import gi.repository
import requests
import spotipy
import spotipy.oauth2

try:
    from IPython import embed as fuck
except:
    pass


WALLIFY_DIR = os.path.realpath(
    os.path.expanduser('~/.wallify')
)


# Poor man's config file
CREATE_BLACK  = True
SCREEN_WIDTH  = 2560
SCREEN_HEIGHT = 1600
ALBUM_SIZE    =  300
ALBUM_SCALE   =    4  # Must be a multiple of 2

# Forgive my alignment autism... damn Haskell
album_width      = ALBUM_SIZE
album_height     = ALBUM_SIZE
central_width    = ALBUM_SIZE * ALBUM_SCALE
central_height   = ALBUM_SIZE * ALBUM_SCALE
wallpaper_width  = SCREEN_WIDTH  + (central_width  - SCREEN_WIDTH  % central_width)
wallpaper_height = SCREEN_HEIGHT + (central_height - SCREEN_HEIGHT % central_height)
repeat_x         = wallpaper_width  // album_width
repeat_y         = wallpaper_height // album_height
# Calc the top-left position of the big image
center_i = (repeat_x - ALBUM_SCALE) // 2
center_j = (repeat_y - ALBUM_SCALE) // 2


class WallpaperSetter(object):
    def set_wallpaper(self, path):
        raise Exception('Not implemented :/')


# https://github.com/pashazz/ksetwallpaper/blob/master/ksetwallpaper.py
KDE_SCRIPT = r"""
var allDesktops = desktops();
print (allDesktops);
for (i=1;i<allDesktops.length;i++) {
    d = allDesktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
    d.writeConfig("FillMode", "2");
    d.writeConfig("Image", "file://IMAGE_PATH");
}
"""


class KdeSetter(WallpaperSetter):
    def __init__(self):
        self.tick = 0

    def set_wallpaper(self, path):
        final_path = f'/tmp/wallify_{self.tick}.png'
        bus = pydbus.SessionBus()
        bus.autoclose = True
        plasma = bus.get('org.kde.plasmashell', '/PlasmaShell')
        shutil.copyfile(path, final_path)
        plasma.evaluateScript(KDE_SCRIPT.replace('IMAGE_PATH', final_path))
        self.tick += 1
        self.tick %= 2


class Wallify(object):
    def __init__(self, client_id, client_secret, wp_setter):
        self.last_image = None
        self.last_track = None
        self.wp_setter  = wp_setter

        # x, y... I know, I know
        self.blocks     = [[False] * repeat_y for _ in range(repeat_x)]
        for i in range(ALBUM_SCALE):
            for j in range(ALBUM_SCALE):
                self.blocks[center_i + i][center_j + j] = True

        credentials_manager = spotipy.oauth2.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        self.client = spotipy.Spotify(client_credentials_manager=credentials_manager)

        self._init_cache()

    def _init_cache(self):
        self.base_path      = WALLIFY_DIR
        self.cache_path     = os.path.join(self.base_path, 'cache')
        self.wallpaper_path = os.path.join(self.base_path, 'wallpaper.png')
        os.makedirs(self.base_path,  exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)

    def download_image(self, url):
        path = self.image_url_to_path(url)

        if not os.path.exists(path):
            urllib.request.urlretrieve(url, path)
            print('Downloaded "{}" to "{}"...'.format(url, path))
        else:
            print('Pulling "{}" from cache...'.format(url))

        return path

    def image_url_to_path(self, url):
        uid = hashlib.md5(url.encode('utf8')).hexdigest()
        return os.path.join(self.cache_path, uid)

    def on_track_info(self, _, data, __):
        if 'Metadata' not in data:
            print('Track info without \'Metadata\' :/')
            return

        track_id = data['Metadata']['mpris:trackid']
        if track_id == self.last_track:
            return
        self.last_track = track_id

        track_info = self.client.track(track_id)

        images = track_info['album']['images']
        image_url = max(images, key=lambda x: x['height'])['url']

        if self.image_url_to_path(image_url) == self.last_image:
            return

        image_path = self.download_image(image_url)
        assert image_path

        self.update_wallpaper_image(image_path)
        self.last_image = image_path
        self.wp_setter.set_wallpaper(self.wallpaper_path)

    def run(self):
        bus = pydbus.SessionBus()
        spotify = bus.get('org.mpris.MediaPlayer2.spotify', '/org/mpris/MediaPlayer2')
        spotify.PropertiesChanged.connect(self.on_track_info)
        gi.repository.GLib.MainLoop().run()

    def update_wallpaper_image(self, image_path):
        src     = PIL.Image.open(image_path)
        central = src.resize((central_width, central_height))
        album   = src.resize((album_width, album_height))

        # Open current wallpaper if existing, otherwise create it
        must_create = True
        if os.path.isfile(self.wallpaper_path):
            must_create = False
            wallpaper = PIL.Image.open(self.wallpaper_path)
            if wallpaper.width != wallpaper_width or wallpaper.height != wallpaper_height:
                must_create = True

        if must_create:
            wallpaper = PIL.Image.new('RGB', (wallpaper_width, wallpaper_height), (0, 0, 0))
            if not CREATE_BLACK:
                for i in range(repeat_x):
                    for j in range(repeat_y):
                        x = i * album_width
                        y = j * album_height
                        wallpaper.paste(album, (x, y))
        
        # Draw the small version of the last album
        if self.last_image:
            last = PIL.Image.open(self.last_image)
            last = last.resize((album_width, album_height))

            while True:
                i = random.randint(0, repeat_x - 1)
                j = random.randint(0, repeat_y - 1)
                filled = sum(sum(a) for a in self.blocks) == repeat_x * repeat_y
                if filled:
                    # If filled, simply avoid writing behind the central block
                    if (center_i <= i < center_i + ALBUM_SCALE) and (center_j <= j < center_j + ALBUM_SCALE):
                        continue
                elif self.blocks[i][j]:
                    # If not filled, we want to avoid already filled blocks
                    continue
                break
            
            x = i * album_width
            y = j * album_height
            self.blocks[i][j] = True
            wallpaper.paste(last, (x, y))

        # Draw the big version of the current album
        x = center_i * album_width
        y = center_j * album_height
        wallpaper.paste(central, (x, y))
        wallpaper.save(self.wallpaper_path)
            

if __name__ == '__main__':
    client_id, client_secret = [l.strip() for l in open('./creds.txt', 'r').readlines()][:2]
    wallify = Wallify(client_id, client_secret, KdeSetter())
    wallify.run()

