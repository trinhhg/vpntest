"""
update_sub.py — VPN Trinh Hg subscription updater

APPROACH MỚI (fix lỗi proxy group not found):
- Fetch b64 (UA: v2rayN) → decode → parse từng proxy URI
- Convert sang Clash proxy dict (tự parse, không dựa vào YAML từ server)
- Build YAML đầy đủ từ scratch → 100% đảm bảo proxy name == group refs
- Không còn vấn đề UA filtering hay sync lệch tên
"""

import requests
import base64
import urllib.parse
import re
import datetime
import yaml

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH  = f"{WORKER_DOMAIN}/api/push_data"

# ─── 4 Node thông tin ────────────────────────────────────────────────────────
INFO_NODES_NEW = [
    "🇻🇳 Truy cập web bên dưới",
    "🇻🇳 Để xem thêm gói khác",
    "🌐 Website: vpntrinhhg.pages.dev",
    "📞 Zalo: 0917678211",
]

INFO_KEYWORDS = ['剩余流量', '距离下次重置', '套餐到期']

GROUP_RENAMES = {
    '顶级机场': 'VPN Trinh Hg',
    '良心云':   'VPN Trinh Hg',
    '自动选择': 'Auto Select',
    '故障转移': 'Fallback',
}

# ─── Bảng rename node cố định ────────────────────────────────────────────────
FIXED_RENAME = {
    '🇺🇸美国洛杉矶1号':        '🇺🇸 US Los Angeles 01 - VPN Trinh Hg',
    '🇺🇸美国洛杉矶2号':        '🇺🇸 US Los Angeles 02 - VPN Trinh Hg',
    '🇺🇸美国洛杉矶3号':        '🇺🇸 US Los Angeles 03 - VPN Trinh Hg',
    '🇺🇸美国凤凰城1号':        '🇺🇸 US Phoenix 01 - VPN Trinh Hg',
    '🇩🇪德国法兰克福2':        '🇩🇪 DE Frankfurt 02 - VPN Trinh Hg',
    '🇧🇷巴西圣保罗-1.5倍率':   '🇧🇷 BR Sao Paulo 1.5x - VPN Trinh Hg',
    '🇦🇪迪拜-1.2倍率':         '🇦🇪 AE Dubai 1.2x - VPN Trinh Hg',
    '🇦🇪迪拜2-1.5倍率':        '🇦🇪 AE Dubai 02 1.5x - VPN Trinh Hg',
    '🇯🇵日本':                 '🇯🇵 JP Japan - VPN Trinh Hg',
    '🇭🇰香港1号':              '🇭🇰 HK Hong Kong 01 - VPN Trinh Hg',
    '🇭🇰香港2号':              '🇭🇰 HK Hong Kong 02 - VPN Trinh Hg',
    '🇭🇰香港3号':              '🇭🇰 HK Hong Kong 03 - VPN Trinh Hg',
    '🇮🇳印度孟买-1.5倍率':     '🇮🇳 IN Mumbai 1.5x - VPN Trinh Hg',
    '🇮🇳印度海得拉巴-1.5倍率': '🇮🇳 IN Hyderabad 1.5x - VPN Trinh Hg',
    '🇬🇧英国伦敦-2倍率':       '🇬🇧 UK London 2.0x - VPN Trinh Hg',
    '🇬🇧英国伦敦2-1.8倍率':    '🇬🇧 UK London 02 1.8x - VPN Trinh Hg',
    '🇿🇦非洲约翰内斯堡-3.5倍率':'🇿🇦 ZA Johannesburg 3.5x - VPN Trinh Hg',
    '🇨🇦加拿大多伦多-1.5倍率': '🇨🇦 CA Toronto 1.5x - VPN Trinh Hg',
    '🇸🇪瑞典斯德哥尔摩-1.5倍率':'🇸🇪 SE Stockholm 1.5x - VPN Trinh Hg',
    '🇲🇽墨西哥克雷塔罗':       '🇲🇽 MX Queretaro - VPN Trinh Hg',
    '🇯🇵日本1号 三网高速':      '🇯🇵 JP Japan 01 Premium - VPN Trinh Hg',
    '🇯🇵日本2号 三网高速':      '🇯🇵 JP Japan 02 Premium - VPN Trinh Hg',
    '🇯🇵日本3号 三网高速':      '🇯🇵 JP Japan 03 Premium - VPN Trinh Hg',
    '🇺🇸美国凤凰城-0.1倍':     '🇺🇸 US Phoenix 0.1x - VPN Trinh Hg',
    '🇺🇸美国1号-0.1倍':        '🇺🇸 US 01 0.1x - VPN Trinh Hg',
    '🇺🇸美国3号-0.1倍':        '🇺🇸 US 03 0.1x - VPN Trinh Hg',
    '🇺🇸美国4号-0.1倍':        '🇺🇸 US 04 0.1x - VPN Trinh Hg',
    '🇯🇵日本-0.1—流媒体':      '🇯🇵 JP Japan 0.1x Streaming - VPN Trinh Hg',
    '🇯🇵日本2-0.1—流媒体':     '🇯🇵 JP Japan 02 0.1x Streaming - VPN Trinh Hg',
    '🇯🇵日本3-0.1—流媒体':     '🇯🇵 JP Japan 03 0.1x Streaming - VPN Trinh Hg',
    '🇯🇵日本4-0.1—流媒体':     '🇯🇵 JP Japan 04 0.1x Streaming - VPN Trinh Hg',
    '🇩🇪德国':                 '🇩🇪 DE Germany - VPN Trinh Hg',
    '🇬🇧英国伦敦-1倍':         '🇬🇧 UK London 1.0x - VPN Trinh Hg',
    '🇹🇼台湾—TK专线':          '🇹🇼 TW Taiwan TK Dedicated - VPN Trinh Hg',
    '🇮🇳印度孟买':             '🇮🇳 IN Mumbai - VPN Trinh Hg',
    '🇭🇰香港高速01|BGP|流媒体': '🇭🇰 HK Hong Kong High Speed 01 Streaming - VPN Trinh Hg',
    '🇭🇰香港高速02|BGP|流媒体': '🇭🇰 HK Hong Kong High Speed 02 Streaming - VPN Trinh Hg',
    '🇭🇰香港高速03|BGP|流媒体': '🇭🇰 HK Hong Kong High Speed 03 Streaming - VPN Trinh Hg',
    '🇭🇰香港高速04|BGP|流媒体': '🇭🇰 HK Hong Kong High Speed 04 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡高速01|BGP|流媒体':'🇸🇬 SG Singapore High Speed 01 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡高速02|BGP|流媒体':'🇸🇬 SG Singapore High Speed 02 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡高速03|BGP|流媒体':'🇸🇬 SG Singapore High Speed 03 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡高速04|BGP|流媒体':'🇸🇬 SG Singapore High Speed 04 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡高速05|BGP|流媒体':'🇸🇬 SG Singapore High Speed 05 Streaming - VPN Trinh Hg',
    '🇯🇵日本高速01|BGP|流媒体': '🇯🇵 JP Japan High Speed 01 Streaming - VPN Trinh Hg',
    '🇯🇵日本高速02|BGP|流媒体': '🇯🇵 JP Japan High Speed 02 Streaming - VPN Trinh Hg',
    '🇯🇵日本高速03|BGP|流媒体': '🇯🇵 JP Japan High Speed 03 Streaming - VPN Trinh Hg',
    '🇯🇵日本高速04|BGP|流媒体': '🇯🇵 JP Japan High Speed 04 Streaming - VPN Trinh Hg',
    '🇯🇵日本高速05|BGP|流媒体': '🇯🇵 JP Japan High Speed 05 Streaming - VPN Trinh Hg',
    '🇯🇵日本高速06|BGP|流媒体': '🇯🇵 JP Japan High Speed 06 Streaming - VPN Trinh Hg',
    '🇺🇸美国高速01|流媒体':     '🇺🇸 US America High Speed 01 Streaming - VPN Trinh Hg',
    '🇺🇸美国高速03|流媒体':     '🇺🇸 US America High Speed 03 Streaming - VPN Trinh Hg',
    '🇺🇸美国高速04|流媒体':     '🇺🇸 US America High Speed 04 Streaming - VPN Trinh Hg',
    '🇰🇷韩国高速01|BGP|流媒体': '🇰🇷 KR South Korea High Speed 01 Streaming - VPN Trinh Hg',
    '🇨🇳台湾高速01|BGP|流媒体': '🇹🇼 TW Taiwan High Speed 01 Streaming - VPN Trinh Hg',
    '🇭🇰香港专线01|BGP|流媒体': '🇭🇰 HK Hong Kong Dedicated 01 Streaming - VPN Trinh Hg',
    '🇭🇰香港专线02|BGP|流媒体': '🇭🇰 HK Hong Kong Dedicated 02 Streaming - VPN Trinh Hg',
    '🇭🇰香港专线03|BGP|流媒体': '🇭🇰 HK Hong Kong Dedicated 03 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡专线02|BGP|流媒体':'🇸🇬 SG Singapore Dedicated 02 Streaming - VPN Trinh Hg',
    '🇸🇬新加坡专线03|BGP|流媒体':'🇸🇬 SG Singapore Dedicated 03 Streaming - VPN Trinh Hg',
    '🇯🇵日本专线01|BGP|流媒体': '🇯🇵 JP Japan Dedicated 01 Streaming - VPN Trinh Hg',
    '🇯🇵日本专线02|BGP|流媒体': '🇯🇵 JP Japan Dedicated 02 Streaming - VPN Trinh Hg',
    '🇯🇵日本专线03|BGP|流媒体': '🇯🇵 JP Japan Dedicated 03 Streaming - VPN Trinh Hg',
    '🇰🇷韩国专线01|BGP|流媒体': '🇰🇷 KR South Korea Dedicated 01 Streaming - VPN Trinh Hg',
    '🇨🇳台湾专线01|BGP|流媒体': '🇹🇼 TW Taiwan Dedicated 01 Streaming - VPN Trinh Hg',
    '🇺🇸美国01|流媒体':         '🇺🇸 US America 01 Streaming - VPN Trinh Hg',
    '🇺🇸美国02|流媒体':         '🇺🇸 US America 02 Streaming - VPN Trinh Hg',
}

def is_info_node(name: str) -> bool:
    return any(k in name for k in INFO_KEYWORDS)

def rename(old: str) -> str:
    return FIXED_RENAME.get(old, old)


# ─────────────────────────────────────────────────────────────────────────────
# PARSE PROXY URI → Clash proxy dict
# ─────────────────────────────────────────────────────────────────────────────
def parse_hysteria2(uri: str) -> dict:
    base = uri.split('#')[0]
    try:
        u = urllib.parse.urlparse(base)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        proxy = {
            'type': 'hysteria2',
            'server': u.hostname,
            'port': u.port or 443,
            'password': urllib.parse.unquote(u.username or ''),
            'udp': True,
            'skip-cert-verify': params.get('insecure', '0') == '1',
        }
        if params.get('sni'):   proxy['sni'] = params['sni']
        if params.get('mport'): proxy['mport'] = params['mport']
        if params.get('ports'): proxy['ports'] = params['ports']
        return proxy
    except Exception as e:
        return None


def parse_vless(uri: str) -> dict:
    base = uri.split('#')[0]
    try:
        u = urllib.parse.urlparse(base)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        security = params.get('security', 'none')
        network = params.get('type', 'tcp')
        proxy = {
            'type': 'vless',
            'server': u.hostname,
            'port': u.port or 443,
            'uuid': u.username or '',
            'udp': True,
            'tls': security in ('tls', 'reality'),
            'skip-cert-verify': params.get('insecure', '0') == '1',
        }
        flow = params.get('flow', '')
        if flow: proxy['flow'] = flow
        fp = params.get('fp', '')
        if fp: proxy['client-fingerprint'] = fp
        sni = params.get('sni', '')
        if sni: proxy['servername'] = sni
        if security == 'reality':
            ro = {}
            if params.get('pbk'): ro['public-key'] = params['pbk']
            if params.get('sid'): ro['short-id'] = params['sid']
            if ro: proxy['reality-opts'] = ro
        if network == 'ws':
            proxy['network'] = 'ws'
            path = urllib.parse.unquote(params.get('path', '/'))
            host = params.get('host', u.hostname)
            proxy['ws-opts'] = {'path': path, 'headers': {'Host': host}}
        elif network == 'grpc':
            proxy['network'] = 'grpc'
            proxy['grpc-opts'] = {'grpc-service-name': params.get('serviceName', '')}
        return proxy
    except Exception:
        return None


def parse_trojan(uri: str) -> dict:
    base = uri.split('#')[0]
    try:
        u = urllib.parse.urlparse(base)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        proxy = {
            'type': 'trojan',
            'server': u.hostname,
            'port': u.port or 443,
            'password': urllib.parse.unquote(u.username or ''),
            'udp': True,
            'skip-cert-verify': params.get('allowInsecure', '0') == '1',
        }
        sni = params.get('sni', params.get('peer', ''))
        if sni: proxy['sni'] = sni
        return proxy
    except Exception:
        return None


def parse_ss(uri: str) -> dict:
    """Shadowsocks: ss://BASE64(method:password)@server:port#name"""
    base = uri.split('#')[0]
    try:
        u = urllib.parse.urlparse(base)
        userinfo = u.username or ''
        try:
            pad = userinfo + '=' * ((-len(userinfo)) % 4)
            decoded = base64.b64decode(pad).decode()
            method, password = decoded.split(':', 1)
        except Exception:
            method = urllib.parse.unquote(userinfo)
            password = u.password or ''
        return {
            'type': 'ss',
            'server': u.hostname,
            'port': u.port or 443,
            'cipher': method,
            'password': password,
            'udp': True,
        }
    except Exception:
        return None


def uri_to_proxy(line: str):
    """Convert một proxy URI string thành Clash proxy dict với name"""
    line = line.strip()
    if not line or '://' not in line:
        return None
    
    # Lấy name từ fragment
    if '#' in line:
        name_encoded = line.split('#', 1)[1]
        name = urllib.parse.unquote(name_encoded)
    else:
        name = None
    
    # Parse theo protocol
    proto = line.split('://')[0].lower()
    proxy = None
    
    if proto == 'hysteria2' or proto == 'hy2':
        proxy = parse_hysteria2(line)
    elif proto == 'vless':
        proxy = parse_vless(line)
    elif proto == 'trojan':
        proxy = parse_trojan(line)
    elif proto in ('ss', 'shadowsocks'):
        proxy = parse_ss(line)
    elif proto == 'vmess':
        # vmess thường là base64 JSON - bỏ qua vì phức tạp
        return None
    
    if proxy and name:
        proxy['name'] = name
    
    return proxy


# ─────────────────────────────────────────────────────────────────────────────
# YAML DUMP helpers (tương tự bản cũ)
# ─────────────────────────────────────────────────────────────────────────────
def _needs_quote(s: str) -> bool:
    if not isinstance(s, str) or not s:
        return True
    specials = ':{}[]|>&*!,#\'"%-?@`'
    return (any(c in s for c in specials) or
            s[0] in '!&*?|-' or
            ' ' in s or
            bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf\U0001f300-\U0001faff]', s)) or
            s.lower() in ('true','false','null','yes','no','on','off'))

def _q(v) -> str:
    if isinstance(v, bool): return str(v).lower()
    if not isinstance(v, str): return str(v)
    if _needs_quote(v): return "'" + v.replace("'", "''") + "'"
    return v

def _proxy_to_inline(p: dict) -> str:
    parts = []
    for k, v in p.items():
        if isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, dict):
            inner = ', '.join(
                f"{ik}: {_q(iv) if isinstance(iv, str) else str(iv).lower() if isinstance(iv, bool) else iv}"
                for ik, iv in v.items()
            )
            parts.append(f"{k}: {{{inner}}}")
        elif isinstance(v, list):
            items = ', '.join(_q(i) if isinstance(i, str) else str(i) for i in v)
            parts.append(f"{k}: [{items}]")
        else:
            parts.append(f"{k}: {_q(v)}")
    return "    - { " + ", ".join(parts) + " }"

def _group_to_inline(g: dict) -> str:
    name  = _q(g['name'])
    gtype = g['type']
    plist = ", ".join(_q(p) for p in g.get('proxies', []))
    line  = f"    - {{ name: {name}, type: {gtype}, proxies: [{plist}]"
    if 'url'       in g: line += f", url: {_q(g['url'])}"
    if 'interval'  in g: line += f", interval: {g['interval']}"
    if 'tolerance' in g: line += f", tolerance: {g['tolerance']}"
    line += " }"
    return line


# ─────────────────────────────────────────────────────────────────────────────
# BUILD YAML ĐẦY ĐỦ TỪ DANH SÁCH PROXY
# ─────────────────────────────────────────────────────────────────────────────

# Header chuẩn Clash Meta / Mihomo
CLASH_HEADER = """mixed-port: 7890
allow-lan: false
bind-address: '*'
mode: rule
log-level: info
external-controller: '127.0.0.1:9090'
unified-delay: true
tcp-concurrent: true
dns:
    enable: true
    ipv6: false
    default-nameserver: [223.5.5.5, 119.29.29.29]
    enhanced-mode: fake-ip
    fake-ip-range: 198.18.0.1/16
    use-hosts: true
    nameserver: ['https://doh.pub/dns-query', 'https://dns.alidns.com/dns-query']
    fallback: ['https://doh.dns.sb/dns-query', 'https://dns.cloudflare.com/dns-query', 'https://dns.twnic.tw/dns-query', 'tls://8.8.4.4:853']
    fallback-filter: { geoip: true, ipcidr: [240.0.0.0/4, 0.0.0.0/32] }"""

# Rules chuẩn
CLASH_RULES = [
    "DOMAIN-SUFFIX,services.googleapis.cn,VPN Trinh Hg",
    "DOMAIN,safebrowsing.urlsec.qq.com,DIRECT",
    "DOMAIN,safebrowsing.googleapis.com,DIRECT",
    "DOMAIN-KEYWORD,google,VPN Trinh Hg",
    "DOMAIN-KEYWORD,gmail,VPN Trinh Hg",
    "DOMAIN-KEYWORD,youtube,VPN Trinh Hg",
    "DOMAIN-KEYWORD,facebook,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fb.me,VPN Trinh Hg",
    "DOMAIN-KEYWORD,twitter,VPN Trinh Hg",
    "DOMAIN-KEYWORD,instagram,VPN Trinh Hg",
    "DOMAIN-KEYWORD,telegram,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegram.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegra.ph,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tiktok.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,github.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,githubusercontent.com,VPN Trinh Hg",
    "DOMAIN-KEYWORD,dropbox,VPN Trinh Hg",
    "DOMAIN-SUFFIX,spotify.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,netflix.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,126.com,DIRECT",
    "DOMAIN-SUFFIX,163.com,DIRECT",
    "DOMAIN-SUFFIX,bilibili.com,DIRECT",
    "DOMAIN-SUFFIX,qq.com,DIRECT",
    "DOMAIN-SUFFIX,weibo.com,DIRECT",
    "DOMAIN-SUFFIX,zhihu.com,DIRECT",
    "DOMAIN-SUFFIX,baidu.com,DIRECT",
    "DOMAIN-KEYWORD,adservice,REJECT",
    "DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-SUFFIX,appsflyer.com,REJECT",
    "DOMAIN,injections.adguard.org,DIRECT",
    "DOMAIN-SUFFIX,local,DIRECT",
    "IP-CIDR,127.0.0.0/8,DIRECT",
    "IP-CIDR,172.16.0.0/12,DIRECT",
    "IP-CIDR,192.168.0.0/16,DIRECT",
    "IP-CIDR,10.0.0.0/8,DIRECT",
    "GEOIP,CN,DIRECT",
    "MATCH,VPN Trinh Hg",
]

# Info node vless fake để đặt ở đầu
INFO_VLESS = {
    'type': 'vless',
    'server': '127.0.0.1',
    'port': 1,
    'uuid': '00000000-0000-0000-0000-000000000000',
    'udp': False,
    'tls': False,
    'skip-cert-verify': True,
}


def build_yaml_from_proxies(proxy_list: list) -> str:
    """
    Build YAML đầy đủ từ danh sách proxy dict.
    proxy_list đã qua rename, đã bỏ info nodes gốc.
    """
    # Tạo 4 info nodes đặt đầu
    final_proxies = []
    for info_name in INFO_NODES_NEW:
        p = dict(INFO_VLESS)
        p['name'] = info_name
        final_proxies.append(p)
    
    # Thêm proxy thực
    real_proxy_names = []
    for p in proxy_list:
        final_proxies.append(p)
        real_proxy_names.append(p['name'])
    
    # Tất cả tên proxy (để đưa vào group)
    all_proxy_names = INFO_NODES_NEW + real_proxy_names
    
    # Build groups
    groups = [
        {
            'name': 'VPN Trinh Hg',
            'type': 'select',
            'proxies': ['Auto Select', 'Fallback'] + all_proxy_names,
        },
        {
            'name': 'Auto Select',
            'type': 'url-test',
            'proxies': real_proxy_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 86400,
            'tolerance': 50,
        },
        {
            'name': 'Fallback',
            'type': 'fallback',
            'proxies': real_proxy_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 7200,
        },
    ]
    
    # Dump
    lines = [CLASH_HEADER, "proxies:"]
    for p in final_proxies:
        lines.append(_proxy_to_inline(p))
    lines.append("proxy-groups:")
    for g in groups:
        lines.append(_group_to_inline(g))
    lines.append("rules:")
    for r in CLASH_RULES:
        lines.append(f"    - {_q(r)}")
    
    result = "\n".join(lines)
    
    # Verify
    try:
        y2 = yaml.safe_load(result)
        pnames = {p['name'] for p in y2.get('proxies', [])}
        gnames = {g['name'] for g in y2.get('proxy-groups', [])}
        all_n = pnames | gnames
        errors = []
        for g in y2.get('proxy-groups', []):
            for ref in g.get('proxies', []):
                if ref not in all_n:
                    errors.append(f"'{ref}' in '{g['name']}'")
        if errors:
            print(f"  [WARN] YAML verify errors: {errors[:3]}")
        else:
            print(f"  [OK] YAML ✅ ({len(pnames)} proxies, {len(gnames)} groups)")
    except Exception as e:
        print(f"  [WARN] YAML verify fail: {e}")
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROCESS B64
# ─────────────────────────────────────────────────────────────────────────────
def process_b64_to_b64_and_yaml(raw_b64: str):
    """
    Từ b64 raw:
    1. Decode → list URIs
    2. Parse từng URI
    3. Rename, bỏ info nodes gốc, thêm info nodes mới
    4. Return (new_b64, yaml_full)
    """
    pad = raw_b64 + '=' * ((-len(raw_b64)) % 4)
    try:
        decoded = base64.b64decode(pad).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [!] b64 decode lỗi: {e}")
        return raw_b64, ""
    
    lines = [l.strip() for l in decoded.splitlines() if l.strip()]
    
    # ── Build new b64 ──
    new_b64_lines = []
    # Info nodes đầu tiên
    for info_name in INFO_NODES_NEW:
        new_b64_lines.append(
            f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:1?type=tcp"
            f"#{urllib.parse.quote(info_name, safe='')}"
        )
    
    # ── Build proxy list cho YAML ──
    proxy_list = []
    
    for line in lines:
        if '://' not in line:
            continue
        
        # Lấy tên gốc
        old_name = None
        if '#' in line:
            old_name = urllib.parse.unquote(line.split('#', 1)[-1])
        
        # Bỏ info nodes gốc
        if old_name and is_info_node(old_name):
            continue
        
        # Rename
        new_name = rename(old_name) if old_name else old_name
        
        # B64: thêm vào new lines với tên mới
        if old_name and new_name:
            new_line = line.split('#')[0] + '#' + urllib.parse.quote(new_name, safe='')
        else:
            new_line = line
        new_b64_lines.append(new_line)
        
        # YAML: parse proxy
        if new_name:
            # Tạo URI với tên mới để parse
            uri_with_new_name = line.split('#')[0] + '#' + urllib.parse.quote(new_name, safe='')
            proxy = uri_to_proxy(uri_with_new_name)
            if proxy and proxy.get('name') and proxy.get('server'):
                proxy_list.append(proxy)
    
    # Build new b64
    new_b64_str = "\n".join(new_b64_lines)
    new_b64 = base64.b64encode(new_b64_str.encode('utf-8')).decode('ascii')
    
    # Build YAML
    yaml_str = ""
    if proxy_list:
        print(f"  [OK] Parsed {len(proxy_list)} proxies from b64")
        yaml_str = build_yaml_from_proxies(proxy_list)
    else:
        print(f"  [!] Không parse được proxy nào từ b64!")
    
    return new_b64, yaml_str


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=15)
        res.raise_for_status()
        links_db = res.json()
        print(f"Tổng link DB: {len(links_db)}")
    except Exception as e:
        print(f"[!] Không lấy được links DB: {e}")
        return
    
    # Chỉ fetch token GỐC duy nhất
    unique_origins = {}
    for item in links_db:
        orig_url = item.get("orig")
        if not orig_url:
            continue
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(orig_url).query)
            tl = qs.get("OwO") or qs.get("token")
            if tl:
                unique_origins[tl[0]] = orig_url
        except Exception:
            continue
    
    print(f"Link gốc cần fetch: {len(unique_origins)}")
    
    for token, orig_url in unique_origins.items():
        print(f"\n→ Token: {token[:12]}...")
        try:
            # Chỉ cần fetch b64 (luôn work)
            b64_res = requests.get(
                orig_url,
                headers={"User-Agent": "v2rayN/6.23"},
                timeout=25
            )
            
            if b64_res.status_code != 200:
                print(f"  [!] HTTP {b64_res.status_code}")
                continue
            
            b64_raw   = b64_res.text.strip()
            user_info = b64_res.headers.get("subscription-userinfo", "")
            
            print(f"  b64 len: {len(b64_raw)} chars")
            
            # Parse traffic
            traffic = {"used":"0.00","total":"0.00","percent":0,"expire":"Vĩnh viễn"}
            if user_info:
                def gi(p):
                    m = re.search(p, user_info)
                    return int(m.group(1)) if m else 0
                up = gi(r'upload=(\d+)'); dn = gi(r'download=(\d+)')
                tot = gi(r'total=(\d+)'); exp = gi(r'expire=(\d+)')
                used_gb  = (up + dn) / 1_073_741_824
                total_gb = tot / 1_073_741_824
                pct = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                exp_str = (datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y')
                           if exp > 0 else "Vĩnh viễn")
                traffic = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}",
                           "percent": pct, "expire": exp_str}
            
            # Process b64 → b64 mới + YAML đầy đủ
            final_b64, final_yaml = process_b64_to_b64_and_yaml(b64_raw)
            
            # Verify b64
            try:
                base64.b64decode(final_b64 + '=' * ((-len(final_b64)) % 4))
                print(f"  [OK] b64 ({len(final_b64)} chars)")
            except Exception as e:
                print(f"  [WARN] b64 verify: {e}")
                final_b64 = b64_raw
            
            # Push lên KV
            payload = {
                "key":       token,
                "body_b64":  final_b64,
                "body_yaml": final_yaml,
                "info":      user_info,
                "traffic":   traffic,
            }
            push_res = requests.post(API_PUSH, json=payload, timeout=15)
            print(f"  [OK] Push → HTTP {push_res.status_code}")
            
        except Exception as e:
            print(f"  [!] Lỗi: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    update_all_subs()
