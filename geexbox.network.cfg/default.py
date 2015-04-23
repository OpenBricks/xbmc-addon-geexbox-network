import os
import sys
import xbmcaddon
import xml.etree.ElementTree as ET

__scriptname__ = "GeeXboX network configuration"
__author__ = "The Geexbox Team"
__url__ = "http://www.geexbox.org"
__version__ = "0.1.2"

__settings__   = xbmcaddon.Addon(id='geexbox.addon.network')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')

ROOTDIR = os.getcwd().replace( ";", "" )

def is_exe(fpath):
  return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def refreshSettings():
  try:
    f = open("/etc/network")
  except Exception as e:
    print "Error: cannot open /etc/network: %s" % e
    return 'error'

  for line in f:
    line = line.strip()
    if len(line) <= 0:
      continue

    if line[0] == '#':
      continue

    s = line.split('=', 1)
    if len(s) != 2:
      continue

    # trim spurious whitespace, unquote value
    s[1] = s[1].strip().strip('"')

    __settings__.setSetting(s[0], s[1])

def Main():
  refreshSettings()
  __settings__.openSettings()
  if is_exe("/bin/update-config-network"):
    execcmd("/bin/update-config-network")
  elif is_exe("/usr/bin/update-config-network"):
    execcmd("/usr/bin/update-config-network")
  else:
    print "Error: cannot find update-config-network!"
    return 'error'
 
def execcmd(cmd):
  (child_stdin, child_stdout, child_stderr) = os.popen3(cmd)
  stderr = child_stderr.readlines()
  stdout = child_stdout.readlines()
  child_stdin.close()
  child_stdout.close()
  child_stderr.close()
  if stderr ==[]:
    print " Cmd Ok result is %s" % stdout
    return stdout
  else:
    print "Error: %s" % stderr
    return 'error'

def search_and_replace(label,values):
  settings_file = "/usr/share/xbmc/addons/geexbox.network.cfg/resources/settings.xml"
  tree = ET.ElementTree(file=settings_file)
  root = tree.getroot()
  for elem in tree.iter('setting') :
    if len(elem.attrib) > 1:
      if elem.attrib['label'] == label:
	elem.set('values', values)
  tree.write(settings_file)

if __name__ == "__main__":
  Main()
