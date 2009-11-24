import httplib
import xml.etree.ElementTree as et
import xml.parsers.expat, socket # for exceptions
import re, urllib
from subprocess import Popen, PIPE

re_loc = re.compile('^(ia\d+\.us\.archive\.org):(/\d/items/(.*))$')
re_remove_xmlns = re.compile(' xmlns="[^"]+"')

def parse_scandata_xml(xml):
    xml = re_remove_xmlns.sub('', xml)
    tree = et.fromstring(xml)
    leaf = None
    leafNum = None
    cover = None
    title = None
    for e in tree.find('pageData'):
        assert e.tag == 'page'
        leaf = int(e.attrib['leafNum'])
        if leaf > 25: # enough
            break
        page_type = e.findtext('pageType')
        if page_type == 'Cover':
            cover = leaf
        elif page_type == 'Title Page' or page_type == 'Title':
            title = leaf
            break
    return (cover, title)

def zip_test(ia_host, ia_path, ia, zip_type):
    conn = httplib.HTTPConnection(ia_host)
    conn.request('HEAD', ia_path + "/" + ia + "_" + zip_type + ".zip")
    r1 = conn.getresponse()
    try:
        assert r1.status in (200, 403, 404)
    except AssertionError:
        print r1.status, r1.reason
        raise
    return r1.status

def find_item(ia):
    ia = ia.strip()
    ret = Popen(["/petabox/sw/bin/find_item.php", ia], stdout=PIPE, stderr=None).communicate()[0]
    if not ret:
        return (None, None)
    assert ret[-1] == '\n'
    loc = ret[:-1]
    m = re_loc.match(loc)
    assert m
    ia_host = m.group(1)
    ia_path = m.group(2)
    assert m.group(3) == ia

    return (ia_host, ia_path)

def find_title_leaf_et(ia_host, ia_path, scandata):
    return parse_scandata_xml(scandata)

def find_img(item_id):
    (ia_host, ia_path) = find_item(item_id)

    if not ia_host:
        print 'no host', item_id, ia_host
        return
    url = 'http://' + ia_host + ia_path + "/" + item_id + "_scandata.xml"
    scandata = None
    try:
        scandata = urllib.urlopen(url).read()
    except:
        pass
    if not scandata or '<book>' not in scandata[:100]:
        url = "http://" + ia_host + "/zipview.php?zip=" + ia_path + "/scandata.zip&file=scandata.xml"
        scandata = urllib.urlopen(url).read()
    assert scandata

    zip_type = 'tif' if item_id.endswith('goog') else 'jp2'
    try:
        status = zip_test(ia_host, ia_path, item_id, zip_type)
    except socket.error:
        print 'socket error:', ia_host
        bad_hosts.add(ia_host)
        return
    if status in (403, 404):
        print zip_type, ' not found:', (ol, item_id)
        return

    (cover, title) = parse_scandata_xml(scandata)
    return {
        'item_id': item_id,
        'ia_host': ia_host, 
        'ia_path': ia_path,
        'cover': cover,
        'title': title
    }

def test_find_img():
    flatland ='flatlandromanceo00abbouoft'
    ret = find_img(flatland)
    assert ret['item_id'] == 'flatlandromanceo00abbouoft'
    assert ret['cover'] == 1 
    assert ret['title'] == 7

def test_find_img():
    item_id = 'cu31924000331631'
    ret = find_img(item_id)
    assert ret['item_id'] == item_id
    assert ret['cover'] is None
    assert ret['title'] == 0