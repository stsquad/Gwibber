
"""
Paths to various Gwibber files and resources
SegPhault (Ryan Paul) - 11/22/2008
"""

import os, sys

PROGRAM_NAME = "gwibber"
UI_DIR_NAME = "ui"
THEME_DIR_NAME = os.path.join(UI_DIR_NAME, "themes")
LAUNCH_DIR = os.path.abspath(sys.path[0])
DATA_DIRS = [LAUNCH_DIR]

try:
  import xdg
  DATA_BASE_DIRS = xdg.BaseDirectory.xdg_data_dirs
  CACHE_BASE_DIR = xdg.BaseDirectory.xdg_cache_home
except:
  DATA_BASE_DIRS = [
    os.path.join(os.path.expanduser("~"), ".local", "share"),
    "/usr/local/share", "/usr/share"]
  CACHE_BASE_DIR = os.path.join(os.path.expanduser("~"), ".cache")

DATA_DIRS += [os.path.join(d, PROGRAM_NAME) for d in DATA_BASE_DIRS]

def get_desktop_file():
  p = os.path.join(LAUNCH_DIR, "gwibber.desktop")
  if os.path.exists(p): return p
  
  for base in DATA_BASE_DIRS:
    p = os.path.join(base, "applications", "gwibber.desktop")
    if os.path.exists(p): return p

def get_theme_paths():
  for base in DATA_DIRS:
    theme_root = os.path.join(base, THEME_DIR_NAME)
    if os.path.exists(theme_root):
      for f in sorted(os.listdir(theme_root)):
        if not f.startswith('.'):
          theme_dir = os.path.join(theme_root, f)
          if os.path.isdir(theme_dir):
            yield theme_dir

def get_theme_path(name):
  for path in get_theme_paths():
    if name == os.path.basename(path):
      return path

def get_themes():
  themes = {}
  for path in get_theme_paths():
    if not os.path.basename(path) in themes:
      themes[os.path.basename(path)] = path
  return themes

def get_ui_asset(asset_name):
  for base in DATA_DIRS:
    asset_path = os.path.join(base, UI_DIR_NAME, asset_name)
    if os.path.exists(asset_path):
      return asset_path
