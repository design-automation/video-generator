def to_xml(str_to_xml):
    return str_to_xml.replace("&","&amp;").replace("<", "&lt;").replace(">", "&gt;")

def to_symbol(str_to_symbol):
    return str_to_symbol.replace("&amp;","&").replace("&lt;", "<").replace("&gt;", ">")