import re

def to_xml(str_to_xml):
    notes = str_to_xml.replace("&","&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")
    notes = re.sub(r"&lt;([/?p].+?)&gt;", "<\g<1>>", notes)
    notes = re.sub(r"&lt;([/?sub].+?)&gt;", "<\g<1>>", notes)
    return notes

def to_symbol(str_to_symbol):
    return str_to_symbol.replace("&amp;","&").replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'")