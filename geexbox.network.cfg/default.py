import os
import sys
import xbmcaddon
import xml.etree.ElementTree as ET

__scriptname__ = "GeeXboX network configuration"
__author__ = "The Geexbox Team"
__url__ = "http://www.geexbox.org"
__version__ = "0.2.1"

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
  f.close

def Main():
  client = search_network_backend()
  if client == "networkmanager":
    ifaces_found = prepare_data(execcmd("nmcli -f DEVICE dev | tail -n +2"))
    ssid_found = prepare_data(execcmd("nmcli -f SSID dev wifi | tail -n +2"))
    search_and_replace('7200',ifaces_found)
    search_and_replace('7620',ssid_found)

  elif client == "connman":
    execcmd("connmanctl enable wifi")
    execcmd("connmanctl scan wifi")
    ssid_found = prepare_data(execcmd("connmanctl services | grep wifi | sed -e 's/^.\{4\}//' -e 's/wifi_.*//'"))
    search_and_replace('7620',ssid_found)
    ifaces_found = prepare_data(execcmd("ifconfig -a | grep Ethernet | sed -e 's/ *Link.*//'"))
    search_and_replace('7200',ifaces_found)

  refreshSettings()
  __settings__.openSettings()

  ssid_temp = __settings__.getSetting("DETECTED_SSID")
  auto_wifi = __settings__.getSetting("USE_DETECTED_SSID")
  if ssid_temp != "":
    if auto_wifi == "true":
      __settings__.setSetting("SSID",ssid_temp)
  __settings__.setSetting("USE_DETECTED_SSID", "false")

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
  settings_file = __cwd__+"/resources/settings.xml"
  tree = ET.ElementTree(file=settings_file)
  root = tree.getroot()
  for elem in tree.iter('setting') :
    if len(elem.attrib) > 1:
      if elem.attrib['label'] == label:
        elem.set('values', values)
  tree.write(settings_file)

def search_network_backend():
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
    s[1] = s[1].strip().strip('"')
    if s[0] == "NETWORK_BACKEND":
      f.close
      return s[1]

def prepare_data(data):
  a=data
  if len(a)>0:
    for i in range(len(a)):
      a[i]=str(a[i]).strip().strip('\'')
    if len(a) == 1:
      return a[0]
    else:
      b=a[0]
      for i in range(1,len(a)):
        b=b+'|'+a[i]
      return b
  else:
    return ' '


if __name__ == "__main__":
  Main()
