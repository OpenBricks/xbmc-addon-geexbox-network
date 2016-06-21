import os
import sys
import xbmcgui
import xbmcaddon
import xml.etree.ElementTree as ET

__scriptname__ = "GeeXboX network configuration"
__author__ = "The Geexbox Team"
__url__ = "http://www.geexbox.org"
__version__ = "0.2.4"

__settings__   = xbmcaddon.Addon(id='geexbox.addon.network')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')

ROOTDIR = os.getcwd().replace( ";", "" )

def is_exe(fpath):
  return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def execcmd(cmd):
  (child_stdin, child_stdout, child_stderr) = os.popen3(cmd)
  stderr = child_stderr.readlines()
  stdout = child_stdout.readlines()
  child_stdin.close()
  child_stdout.close()
  child_stderr.close()
  if stderr == []:
    print " Cmd Ok result is %s" % stdout
    return stdout
  print "Error: %s" % stderr
  return 'error'

def loadNetworkConfig():
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

    if s[0] != "ADDRESS":
      continue

    # ip address and net mask from 'slashed' form
    am = s[1].split('/', 1)
    __settings__.setSetting("NETADDR", am[0])

    msk = ""
    if len(am) == 2:
      m = -(1 << (32 - int(am[1])))
    else:
      m = -256
    for i in (24,16,8,0):
      msk = msk + '.' + str((m >> i) & 255)
    __settings__.setSetting("NETMASK", msk[1:])

  f.close

def search_and_replace(label,values):
  settings_file = __cwd__ + "/resources/settings.xml"
  tree = ET.ElementTree(file=settings_file)
  root = tree.getroot()
  for elem in tree.iter('setting'):
    if len(elem.attrib) > 1 and elem.attrib['label'] == label:
      elem.set('values', values)
  tree.write(settings_file)

def prepare_data(data):
  if len(data) <= 0:
    return ' '
  a = data
  for i in range(len(a)):
    a[i] = str(a[i]).strip().strip('\'')
  if len(a) == 1:
    return a[0]
  b = a[0]
  for i in range(1, len(a)):
    b = b + '|' + a[i]
  return b

def set_ip(label, value, suffix):
  if value == "" or value == "0.0.0.0":
    __settings__.setSetting(label, "")
  else:
    __settings__.setSetting(label, value + suffix)

def Main():
  try:
    busy_dlg = xbmcgui.DialogProgress()
    busy_dlg.create(__scriptname__, __settings__.getLocalizedString(32300))
    may_cancel = 1
  except AttributeError:
    busy_dlg = xbmcgui.WindowXML("DialogBusy.xml", __cwd__.decode("utf-8"))
    busy_dlg.show()
    may_cancel = 0

  loadNetworkConfig()
  client = __settings__.getSetting("NETWORK_BACKEND")

  if client == "networkmanager":
    ssid_found = prepare_data(execcmd("nmcli -f SSID dev wifi | tail -n +2"))
    ifaces_found = prepare_data(execcmd("nmcli -f DEVICE dev | tail -n +2"))
  elif client == "connman":
    execcmd("connmanctl enable wifi")
    execcmd("connmanctl scan wifi")
    ssid_found = prepare_data(execcmd("connmanctl services | grep wifi | sed -e 's/^.\{4\}//' -e 's/wifi_.*//'"))
    ifaces_found = prepare_data(execcmd("ifconfig -a | grep Ethernet | sed -e 's/ *Link.*//'"))
  else:
    ssid_found = " "
    ifaces_found = "eth0|eth1|wlan0"

  if may_cancel and busy_dlg.iscanceled():
    return

  search_and_replace('32020', ifaces_found)
  search_and_replace('32062', ssid_found)

  busy_dlg.close()

  __settings__.openSettings()

  # retrieve detected SSID
  ssid_temp = __settings__.getSetting("DETECTED_SSID")
  auto_wifi = __settings__.getSetting("USE_DETECTED_SSID")
  if auto_wifi == "true" and ssid_temp != "":
    __settings__.setSetting("SSID", ssid_temp)
  __settings__.setSetting("USE_DETECTED_SSID", "false")

  # convert ip address and netmask to 'slash form'
  adr = __settings__.getSetting("NETADDR")
  msk = __settings__.getSetting("NETMASK").split('.', 4)
  cnt = 0
  for i in range(0,31):
    if ((int(msk[i / 8]) << (i % 8)) & 128) == 0:
      break
    cnt = cnt + 1
  set_ip("ADDRESS", adr, '/' + str(cnt))
  set_ip("GATEWAY", __settings__.getSetting("GATEWAY"), "")
  set_ip("DNS_SERVER", __settings__.getSetting("DNS_SERVER"), "")


  if is_exe("/bin/update-config-network"):
    execcmd("/bin/update-config-network")
  elif is_exe("/usr/bin/update-config-network"):
    execcmd("/usr/bin/update-config-network")
  else:
    print "Error: cannot find update-config-network!"
    return 'error'

if __name__ == "__main__":
  Main()
