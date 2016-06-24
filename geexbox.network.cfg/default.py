import os
import sys
import time
import hashlib
import xbmcgui
import xbmcaddon
import xml.etree.ElementTree as ET

__scriptname__ = "GeeXboX network configuration"
__author__     = "The Geexbox Team"
__url__        = "http://www.geexbox.org"
__version__    = "0.2.6"

__settings__   = xbmcaddon.Addon(id='geexbox.addon.network')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')

ROOTDIR = os.getcwd().replace( ";", "" )

# check, if a file is executable
def is_exe(fpath):
  return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

# execute program and retrieve it's stdout as string list
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
  return []

# import settings from /etc/network(2), calculate checksum
def loadNetworkConfig(cfgFile, suffix):
  try:
    f = open(cfgFile)
  except Exception as e:
    print "Error: cannot open %s: %s" % (cfgFile, e)
    return 'error'

  h = hashlib.md5()
  for line in f:
    s = []
    line = line.strip()
    h.update(line)

    if len(line) > 0 and line[0] != '#':
      s = line.split('=', 1)
    if len(s) != 2:
      continue

    # trim spurious whitespace, unquote value
    s[1] = s[1].strip().strip('"')
    __settings__.setSetting(s[0] + suffix, s[1])

    if s[0] != "ADDRESS":
      continue

    # ip address and net mask from 'slashed' form
    am = s[1].split('/', 1)
    __settings__.setSetting("NETADDR" + suffix, am[0])

    msk = ""
    if len(am) == 2:
      m = -(1 << (32 - int(am[1])))
    else:
      m = -256
    for i in (24,16,8,0):
      msk = msk + '.' + str((m >> i) & 255)
    __settings__.setSetting("NETMASK" + suffix, msk[1:])

  f.close
  return h.hexdigest()

# export settings to /etc/network(2), check for checksum change
def saveNetworkConfig(cfgFile, suffix, chksum):
  try:
    f = open(cfgFile)
  except Exception as e:
    print "Error: cannot open %s: %s" % (cfgFile, e)
    return 0

  tmpFile = cfgFile + ".$$$"
  o = open(tmpFile, "w")

  h = hashlib.md5()
  for line in f:
    s = []
    line = line.strip()
    if len(line) > 0 and line[0] != '#':
      s = line.split('=', 1)
    if len(s) == 2:
      line = "%s=\"%s\"" % (s[0], __settings__.getSetting(s[0] + suffix))

    h.update(line)
    o.write(line + '\n')

  o.close()
  f.close()

  if h.hexdigest() == chksum:
    os.remove(tmpFile)
    return 0
  
  os.remove(cfgFile)
  os.rename(tmpFile, cfgFile)
  return 1

# inject detected information into GUI *.xml
def search_and_replace(guiFile, label, values):
  tree = ET.ElementTree(file=guiFile)
  root = tree.getroot()
  for elem in tree.iter('setting'):
    if len(elem.attrib) > 1 and elem.attrib['label'] == label:
      elem.set('values', values)
  tree.write(guiFile)

# convert string list to string using '|' as separator
def prepare_data(data):
  if len(data) <= 0:
    return "-"
  a = data
  for i in range(len(a)):
    a[i] = str(a[i]).strip().strip('\'')
  if len(a) == 1:
    return a[0]
  b = a[0]
  for i in range(1, len(a)):
    b = b + '|' + a[i]
  return b

# write ip address, optionally with net mask in slash notation
def set_ip(label, value, suffix):
  if value == "" or value == "0.0.0.0":
    __settings__.setSetting(label, "")
  else:
    __settings__.setSetting(label, value + suffix)

# restart network services
def reload_network_backend(name):
  restart_list = [ \
    "telnetd.socket", "sshd.socket", \
    name + ".service", "bftpd.service", \
    "lighttpd.service", "smbd.service", "nmbd.service" ]

  # always execute this first...
  os.system("systemctl restart network-link.service")

  args = ""
  for unit in restart_list:
    if os.access("/lib/systemd/system/" + unit, os.F_OK):
      args = args + ' ' + unit 

  if args != "":
    time.sleep(1)
    os.system("systemctl restart" + args)

# main entry
def Main():
  # create progress dialog (special handling for Frodo)
  try:
    busy_dlg = xbmcgui.DialogProgress()
    busy_dlg.create(__scriptname__, __settings__.getLocalizedString(32300))
    may_cancel = 1
  except AttributeError:
    busy_dlg = xbmcgui.WindowXML("DialogBusy.xml", __cwd__.decode("utf-8"))
    busy_dlg.show()
    may_cancel = 0

  chksum1 = loadNetworkConfig("/etc/network", "")
  chksum2 = loadNetworkConfig("/etc/network2", "2")

  client = __settings__.getSetting("NETWORK_BACKEND")
  __settings__.setSetting("NETWORK_BACKEND2", client)

  if client == "networkmanager":
    ssid_found = prepare_data(execcmd("nmcli -f SSID dev wifi | tail -n +2"))
    ifaces_found = prepare_data(execcmd("nmcli -f DEVICE dev | tail -n +2"))
  elif client == "connman":
    os.system("connmanctl enable wifi; connmanctl scan wifi")
    ssid_found = prepare_data(execcmd("connmanctl services | grep wifi | sed -e 's/^.\{4\}//' -e 's/wifi_.*//'"))
    ifaces_found = prepare_data(execcmd("ifconfig -a | grep Ethernet | sed -e 's/ *Link.*//'"))
  else:
    ssid_found = "-"
    ifaces_found = "-"

  if may_cancel and busy_dlg.iscanceled():
    return

  if ifaces_found == "-":
    ifaces_found = "eth0|eth1|wlan0"

  dialog_file = __cwd__ + "/resources/settings.xml"
  search_and_replace(dialog_file, '32020', ifaces_found)
  search_and_replace(dialog_file, '32120', ifaces_found)
  search_and_replace(dialog_file, '32062', ssid_found)
  search_and_replace(dialog_file, '32162', ssid_found)

  busy_dlg.close()

  __settings__.openSettings()

  for suffix in ("","2"):
    # retrieve detected SSID
    ssid_temp = __settings__.getSetting("DETECTED_SSID" + suffix)
    auto_wifi = __settings__.getSetting("USE_DETECTED_SSID" + suffix)
    if auto_wifi == "true" and ssid_temp != "-":
      __settings__.setSetting("SSID" + suffix, ssid_temp)
    __settings__.setSetting("USE_DETECTED_SSID" + suffix, "false")

    # convert ip address and netmask to 'slash form'
    adr = __settings__.getSetting("NETADDR" + suffix)
    msk = __settings__.getSetting("NETMASK" + suffix).split('.', 4)
    cnt = 0
    for i in range(0,31):
      if ((int(msk[i / 8]) << (i % 8)) & 128) == 0:
        break
      cnt = cnt + 1

    set_ip("ADDRESS" + suffix, adr, '/' + str(cnt))
    set_ip("GATEWAY" + suffix, __settings__.getSetting("GATEWAY" + suffix), "")
    set_ip("DNS_SERVER" + suffix, __settings__.getSetting("DNS_SERVER" + suffix), "")

  changed = 0
  changed = changed + saveNetworkConfig("/etc/network", "", chksum1)
  changed = changed + saveNetworkConfig("/etc/network2", "2", chksum2)
  
  if changed != 0:
    reload_network_backend(client)

if __name__ == "__main__":
  Main()
