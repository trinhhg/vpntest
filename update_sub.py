"""
update_sub.py — VPN Trinh Hg
GitHub Actions: chạy mỗi 60 phút
- Fetch b64 từ link gốc
- Parse từng proxy URI (không fetch YAML server vì UA filtering)
- Build YAML đầy đủ với DNS/rules riêng cho Liangxin và DJJC
- Push lên Cloudflare KV qua /api/push_data
"""

import requests, base64, urllib.parse, re, datetime, yaml, json, sys

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH  = f"{WORKER_DOMAIN}/api/push_data"

# ── Info nodes mặc định ──────────────────────────────────────────────────────
INFO_NODES = [
    "🇻🇳 Truy cập web bên dưới",
    "🇻🇳 Để xem thêm gói khác",
    "🌐 Website: vpntrinhhg.pages.dev",
    "📞 Zalo: 0917678211",
]
INFO_SKIP_KW = ["剩余流量", "距离下次重置", "套餐到期"]

# ── Rename dict DJJC ─────────────────────────────────────────────────────────
RENAME_DJJC = {
    "🇺🇸美国洛杉矶1号":        "🇺🇸 US Los Angeles 01 - VPN Trinh Hg",
    "🇺🇸美国洛杉矶2号":        "🇺🇸 US Los Angeles 02 - VPN Trinh Hg",
    "🇺🇸美国洛杉矶3号":        "🇺🇸 US Los Angeles 03 - VPN Trinh Hg",
    "🇺🇸美国凤凰城1号":        "🇺🇸 US Phoenix 01 - VPN Trinh Hg",
    "🇩🇪德国法兰克福2":        "🇩🇪 DE Frankfurt 02 - VPN Trinh Hg",
    "🇧🇷巴西圣保罗-1.5倍率":   "🇧🇷 BR Sao Paulo 1.5x - VPN Trinh Hg",
    "🇦🇪迪拜-1.2倍率":         "🇦🇪 AE Dubai 1.2x - VPN Trinh Hg",
    "🇦🇪迪拜2-1.5倍率":        "🇦🇪 AE Dubai 02 1.5x - VPN Trinh Hg",
    "🇯🇵日本":                 "🇯🇵 JP Japan - VPN Trinh Hg",
    "🇭🇰香港1号":              "🇭🇰 HK Hong Kong 01 - VPN Trinh Hg",
    "🇭🇰香港2号":              "🇭🇰 HK Hong Kong 02 - VPN Trinh Hg",
    "🇭🇰香港3号":              "🇭🇰 HK Hong Kong 03 - VPN Trinh Hg",
    "🇮🇳印度孟买-1.5倍率":     "🇮🇳 IN Mumbai 1.5x - VPN Trinh Hg",
    "🇮🇳印度海得拉巴-1.5倍率": "🇮🇳 IN Hyderabad 1.5x - VPN Trinh Hg",
    "🇬🇧英国伦敦-2倍率":       "🇬🇧 UK London 2.0x - VPN Trinh Hg",
    "🇬🇧英国伦敦2-1.8倍率":    "🇬🇧 UK London 02 1.8x - VPN Trinh Hg",
    "🇿🇦非洲约翰内斯堡-3.5倍率":"🇿🇦 ZA Johannesburg 3.5x - VPN Trinh Hg",
    "🇨🇦加拿大多伦多-1.5倍率": "🇨🇦 CA Toronto 1.5x - VPN Trinh Hg",
    "🇸🇪瑞典斯德哥尔摩-1.5倍率":"🇸🇪 SE Stockholm 1.5x - VPN Trinh Hg",
    "🇲🇽墨西哥克雷塔罗":       "🇲🇽 MX Queretaro - VPN Trinh Hg",
    "🇯🇵日本1号 三网高速":      "🇯🇵 JP Japan 01 Premium - VPN Trinh Hg",
    "🇯🇵日本2号 三网高速":      "🇯🇵 JP Japan 02 Premium - VPN Trinh Hg",
    "🇯🇵日本3号 三网高速":      "🇯🇵 JP Japan 03 Premium - VPN Trinh Hg",
    "🇺🇸美国凤凰城-0.1倍":     "🇺🇸 US Phoenix 0.1x - VPN Trinh Hg",
    "🇺🇸美国1号-0.1倍":        "🇺🇸 US 01 0.1x - VPN Trinh Hg",
    "🇺🇸美国3号-0.1倍":        "🇺🇸 US 03 0.1x - VPN Trinh Hg",
    "🇺🇸美国4号-0.1倍":        "🇺🇸 US 04 0.1x - VPN Trinh Hg",
    "🇯🇵日本-0.1—流媒体":      "🇯🇵 JP Japan 0.1x Streaming - VPN Trinh Hg",
    "🇯🇵日本2-0.1—流媒体":     "🇯🇵 JP Japan 02 0.1x Streaming - VPN Trinh Hg",
    "🇯🇵日本3-0.1—流媒体":     "🇯🇵 JP Japan 03 0.1x Streaming - VPN Trinh Hg",
    "🇯🇵日本4-0.1—流媒体":     "🇯🇵 JP Japan 04 0.1x Streaming - VPN Trinh Hg",
    "🇩🇪德国":                 "🇩🇪 DE Germany - VPN Trinh Hg",
    "🇬🇧英国伦敦-1倍":         "🇬🇧 UK London 1.0x - VPN Trinh Hg",
    "🇹🇼台湾—TK专线":          "🇹🇼 TW Taiwan TK Dedicated - VPN Trinh Hg",
    "🇮🇳印度孟买":             "🇮🇳 IN Mumbai - VPN Trinh Hg",
}

# ── Rename dict Liangxin ─────────────────────────────────────────────────────
RENAME_LIANGXIN = {
    "🇭🇰香港高速01|BGP|流媒体": "🇭🇰 HK Hong Kong High Speed 01 Streaming - VPN Trinh Hg",
    "🇭🇰香港高速02|BGP|流媒体": "🇭🇰 HK Hong Kong High Speed 02 Streaming - VPN Trinh Hg",
    "🇭🇰香港高速03|BGP|流媒体": "🇭🇰 HK Hong Kong High Speed 03 Streaming - VPN Trinh Hg",
    "🇭🇰香港高速04|BGP|流媒体": "🇭🇰 HK Hong Kong High Speed 04 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡高速01|BGP|流媒体":"🇸🇬 SG Singapore High Speed 01 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡高速02|BGP|流媒体":"🇸🇬 SG Singapore High Speed 02 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡高速03|BGP|流媒体":"🇸🇬 SG Singapore High Speed 03 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡高速04|BGP|流媒体":"🇸🇬 SG Singapore High Speed 04 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡高速05|BGP|流媒体":"🇸🇬 SG Singapore High Speed 05 Streaming - VPN Trinh Hg",
    "🇯🇵日本高速01|BGP|流媒体": "🇯🇵 JP Japan High Speed 01 Streaming - VPN Trinh Hg",
    "🇯🇵日本高速02|BGP|流媒体": "🇯🇵 JP Japan High Speed 02 Streaming - VPN Trinh Hg",
    "🇯🇵日本高速03|BGP|流媒体": "🇯🇵 JP Japan High Speed 03 Streaming - VPN Trinh Hg",
    "🇯🇵日本高速04|BGP|流媒体": "🇯🇵 JP Japan High Speed 04 Streaming - VPN Trinh Hg",
    "🇯🇵日本高速05|BGP|流媒体": "🇯🇵 JP Japan High Speed 05 Streaming - VPN Trinh Hg",
    "🇯🇵日本高速06|BGP|流媒体": "🇯🇵 JP Japan High Speed 06 Streaming - VPN Trinh Hg",
    "🇺🇸美国高速01|流媒体":     "🇺🇸 US America High Speed 01 Streaming - VPN Trinh Hg",
    "🇺🇸美国高速03|流媒体":     "🇺🇸 US America High Speed 03 Streaming - VPN Trinh Hg",
    "🇺🇸美国高速04|流媒体":     "🇺🇸 US America High Speed 04 Streaming - VPN Trinh Hg",
    "🇰🇷韩国高速01|BGP|流媒体": "🇰🇷 KR South Korea High Speed 01 Streaming - VPN Trinh Hg",
    "🇨🇳台湾高速01|BGP|流媒体": "🇹🇼 TW Taiwan High Speed 01 Streaming - VPN Trinh Hg",
    "🇭🇰香港专线01|BGP|流媒体": "🇭🇰 HK Hong Kong Dedicated 01 Streaming - VPN Trinh Hg",
    "🇭🇰香港专线02|BGP|流媒体": "🇭🇰 HK Hong Kong Dedicated 02 Streaming - VPN Trinh Hg",
    "🇭🇰香港专线03|BGP|流媒体": "🇭🇰 HK Hong Kong Dedicated 03 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡专线02|BGP|流媒体":"🇸🇬 SG Singapore Dedicated 02 Streaming - VPN Trinh Hg",
    "🇸🇬新加坡专线03|BGP|流媒体":"🇸🇬 SG Singapore Dedicated 03 Streaming - VPN Trinh Hg",
    "🇯🇵日本专线01|BGP|流媒体": "🇯🇵 JP Japan Dedicated 01 Streaming - VPN Trinh Hg",
    "🇯🇵日本专线02|BGP|流媒体": "🇯🇵 JP Japan Dedicated 02 Streaming - VPN Trinh Hg",
    "🇯🇵日本专线03|BGP|流媒体": "🇯🇵 JP Japan Dedicated 03 Streaming - VPN Trinh Hg",
    "🇰🇷韩国专线01|BGP|流媒体": "🇰🇷 KR South Korea Dedicated 01 Streaming - VPN Trinh Hg",
    "🇨🇳台湾专线01|BGP|流媒体": "🇹🇼 TW Taiwan Dedicated 01 Streaming - VPN Trinh Hg",
    "🇺🇸美国01|流媒体":         "🇺🇸 US America 01 Streaming - VPN Trinh Hg",
    "🇺🇸美国02|流媒体":         "🇺🇸 US America 02 Streaming - VPN Trinh Hg",
}

# ── DNS header riêng cho từng nhà cung cấp ───────────────────────────────────
DJJC_DNS = """\
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

LIANGXIN_DNS = """\
dns:
    enable: true
    ipv6: false
    default-nameserver: [223.5.5.5, 119.29.29.29, 114.114.114.114]
    enhanced-mode: fake-ip
    fake-ip-range: 198.18.0.1/16
    use-hosts: true
    respect-rules: true
    proxy-server-nameserver: [223.5.5.5, 119.29.29.29, 114.114.114.114]
    nameserver: [223.5.5.5, 119.29.29.29, 114.114.114.114]
    fallback: [1.1.1.1, 8.8.8.8]
    fallback-filter: { geoip: true, geoip-code: CN, geosite: [gfw], ipcidr: [240.0.0.0/4], domain: [+.google.com, +.facebook.com, +.youtube.com] }"""

# ── Rules đầy đủ (thay group name bằng "VPN Trinh Hg") ───────────────────────
FULL_RULES = [
    "DOMAIN-SUFFIX,services.googleapis.cn,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xn--ngstr-lra8j.com,VPN Trinh Hg",
    "DOMAIN,safebrowsing.urlsec.qq.com,DIRECT",
    "DOMAIN,safebrowsing.googleapis.com,DIRECT",
    "DOMAIN,developer.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,digicert.com,VPN Trinh Hg",
    "DOMAIN,ocsp.apple.com,VPN Trinh Hg",
    "DOMAIN,ocsp.comodoca.com,VPN Trinh Hg",
    "DOMAIN,ocsp.usertrust.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apple-dns.net,VPN Trinh Hg",
    "DOMAIN,testflight.apple.com,VPN Trinh Hg",
    "DOMAIN,itunes.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apps.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mzstatic.com,DIRECT",
    "DOMAIN-SUFFIX,itunes.apple.com,DIRECT",
    "DOMAIN-SUFFIX,icloud.com,DIRECT",
    "DOMAIN-SUFFIX,icloud-content.com,DIRECT",
    "DOMAIN-SUFFIX,me.com,DIRECT",
    "DOMAIN-SUFFIX,aaplimg.com,DIRECT",
    "DOMAIN-SUFFIX,cdn-apple.com,DIRECT",
    "DOMAIN-SUFFIX,akadns.net,DIRECT",
    "DOMAIN-SUFFIX,akamaiedge.net,DIRECT",
    "DOMAIN-SUFFIX,edgekey.net,DIRECT",
    "DOMAIN-SUFFIX,apple.com,DIRECT",
    "DOMAIN-SUFFIX,apple-cloudkit.com,DIRECT",
    "DOMAIN-SUFFIX,apple-mapkit.com,DIRECT",
    "DOMAIN-SUFFIX,126.com,DIRECT",
    "DOMAIN-SUFFIX,163.com,DIRECT",
    "DOMAIN-SUFFIX,bilibili.com,DIRECT",
    "DOMAIN-SUFFIX,bilivideo.com,DIRECT",
    "DOMAIN-KEYWORD,alicdn,DIRECT",
    "DOMAIN-KEYWORD,alipay,DIRECT",
    "DOMAIN-KEYWORD,taobao,DIRECT",
    "DOMAIN-KEYWORD,baidu,DIRECT",
    "DOMAIN-SUFFIX,bdimg.com,DIRECT",
    "DOMAIN-SUFFIX,bdstatic.com,DIRECT",
    "DOMAIN-SUFFIX,qq.com,DIRECT",
    "DOMAIN-SUFFIX,weibo.com,DIRECT",
    "DOMAIN-SUFFIX,zhihu.com,DIRECT",
    "DOMAIN-SUFFIX,microsoft.com,DIRECT",
    "DOMAIN-SUFFIX,microsoftonline.com,DIRECT",
    "DOMAIN-SUFFIX,miui.com,DIRECT",
    "DOMAIN-SUFFIX,netease.com,DIRECT",
    "DOMAIN-SUFFIX,office.com,DIRECT",
    "DOMAIN-SUFFIX,office365.com,DIRECT",
    "DOMAIN-SUFFIX,mi.com,DIRECT",
    "DOMAIN-SUFFIX,tencent.com,DIRECT",
    "DOMAIN-SUFFIX,jd.com,DIRECT",
    "DOMAIN-SUFFIX,taobao.com,DIRECT",
    "DOMAIN-SUFFIX,tmall.com,DIRECT",
    "DOMAIN-KEYWORD,admarvel,REJECT",
    "DOMAIN-KEYWORD,admaster,REJECT",
    "DOMAIN-KEYWORD,adsage,REJECT",
    "DOMAIN-KEYWORD,adwords,REJECT",
    "DOMAIN-KEYWORD,adservice,REJECT",
    "DOMAIN-SUFFIX,appsflyer.com,REJECT",
    "DOMAIN-KEYWORD,domob,REJECT",
    "DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-SUFFIX,mmstat.com,REJECT",
    "DOMAIN-KEYWORD,mopub,REJECT",
    "DOMAIN-KEYWORD,umeng,REJECT",
    "DOMAIN-SUFFIX,vungle.com,REJECT",
    "DOMAIN-KEYWORD,amazon,VPN Trinh Hg",
    "DOMAIN-KEYWORD,google,VPN Trinh Hg",
    "DOMAIN-KEYWORD,gmail,VPN Trinh Hg",
    "DOMAIN-KEYWORD,youtube,VPN Trinh Hg",
    "DOMAIN-KEYWORD,facebook,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fb.me,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fbcdn.net,VPN Trinh Hg",
    "DOMAIN-KEYWORD,twitter,VPN Trinh Hg",
    "DOMAIN-KEYWORD,instagram,VPN Trinh Hg",
    "DOMAIN-KEYWORD,dropbox,VPN Trinh Hg",
    "DOMAIN-SUFFIX,twimg.com,VPN Trinh Hg",
    "DOMAIN-KEYWORD,blogspot,VPN Trinh Hg",
    "DOMAIN-SUFFIX,youtu.be,VPN Trinh Hg",
    "DOMAIN-KEYWORD,whatsapp,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tiktok.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tiktokv.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegram.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegra.ph,VPN Trinh Hg",
    "DOMAIN-SUFFIX,github.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,githubusercontent.com,VPN Trinh Hg",
    "DOMAIN-KEYWORD,github,VPN Trinh Hg",
    "DOMAIN-SUFFIX,netflix.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,spotify.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,discord.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,discordapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,linkedin.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,line-apps.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bing.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,medium.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pixiv.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,reddit.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,twitch.tv,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vimeo.com,VPN Trinh Hg",
    "IP-CIDR,91.108.4.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.8.0/21,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.16.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.56.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,149.154.160.0/20,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:67c:4e8::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23d::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23f::/48,VPN Trinh Hg,no-resolve",
    "DOMAIN,injections.adguard.org,DIRECT",
    "DOMAIN-SUFFIX,local,DIRECT",
    "IP-CIDR,127.0.0.0/8,DIRECT",
    "IP-CIDR,172.16.0.0/12,DIRECT",
    "IP-CIDR,192.168.0.0/16,DIRECT",
    "IP-CIDR,10.0.0.0/8,DIRECT",
    "IP-CIDR,17.0.0.0/8,DIRECT",
    "IP-CIDR,100.64.0.0/10,DIRECT",
    "IP-CIDR,224.0.0.0/4,DIRECT",
    "IP-CIDR6,fe80::/10,DIRECT",
    "DOMAIN-SUFFIX,cn,DIRECT",
    "DOMAIN-KEYWORD,-cn,DIRECT",
    "GEOIP,CN,DIRECT",
    "MATCH,VPN Trinh Hg",
]


# ── Parse proxy URI ──────────────────────────────────────────────────────────
def parse_hysteria2(uri: str) -> dict | None:
    base = uri.split("#")[0]
    try:
        u = urllib.parse.urlparse(base)
        p = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        proxy = {
            "type": "hysteria2",
            "server": u.hostname,
            "port": u.port or 443,
            "password": urllib.parse.unquote(u.username or ""),
            "udp": True,
            "skip-cert-verify": p.get("insecure", "0") == "1",
        }
        if p.get("sni"):   proxy["sni"]   = p["sni"]
        if p.get("mport"): proxy["mport"] = p["mport"]
        if p.get("ports"): proxy["ports"] = p["ports"]
        return proxy
    except Exception:
        return None


def parse_vless(uri: str) -> dict | None:
    base = uri.split("#")[0]
    try:
        u = urllib.parse.urlparse(base)
        p = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        sec = p.get("security", "none")
        net = p.get("type", "tcp")
        proxy = {
            "type": "vless",
            "server": u.hostname,
            "port": u.port or 443,
            "uuid": u.username or "",
            "udp": True,
            "tls": sec in ("tls", "reality"),
            "skip-cert-verify": p.get("insecure", "0") == "1",
        }
        if p.get("flow"): proxy["flow"] = p["flow"]
        if p.get("fp"):   proxy["client-fingerprint"] = p["fp"]
        if p.get("sni"):  proxy["servername"] = p["sni"]
        if sec == "reality":
            ro = {}
            if p.get("pbk"): ro["public-key"] = p["pbk"]
            if p.get("sid"): ro["short-id"]   = p["sid"]
            if ro: proxy["reality-opts"] = ro
        if net == "ws":
            proxy["network"] = "ws"
            proxy["ws-opts"] = {
                "path": urllib.parse.unquote(p.get("path", "/")),
                "headers": {"Host": p.get("host", u.hostname)},
            }
        elif net == "grpc":
            proxy["network"] = "grpc"
            proxy["grpc-opts"] = {"grpc-service-name": p.get("serviceName", "")}
        return proxy
    except Exception:
        return None


def parse_trojan(uri: str) -> dict | None:
    base = uri.split("#")[0]
    try:
        u = urllib.parse.urlparse(base)
        p = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        proxy = {
            "type": "trojan",
            "server": u.hostname,
            "port": u.port or 443,
            "password": urllib.parse.unquote(u.username or ""),
            "udp": True,
            "skip-cert-verify": p.get("allowInsecure", "0") == "1",
        }
        if p.get("sni"): proxy["sni"] = p["sni"]
        return proxy
    except Exception:
        return None


def uri_to_proxy(line: str) -> dict | None:
    line = line.strip()
    if "://" not in line:
        return None
    proto = line.split("://")[0].lower()
    name = None
    if "#" in line:
        name = urllib.parse.unquote(line.split("#", 1)[-1])
    proxy = None
    if proto in ("hysteria2", "hy2"):
        proxy = parse_hysteria2(line)
    elif proto == "vless":
        proxy = parse_vless(line)
    elif proto == "trojan":
        proxy = parse_trojan(line)
    if proxy and name:
        proxy["name"] = name
    return proxy if (proxy and proxy.get("name") and proxy.get("server")) else None


# ── YAML dump helpers ────────────────────────────────────────────────────────
def _q(v) -> str:
    if isinstance(v, bool): return str(v).lower()
    if not isinstance(v, str): return str(v)
    need = any(c in v for c in ':{}[]|>&*!,#\'"%-?@`') or v[0:1] in "!&*?|-" or " " in v
    if not need:
        need = bool(re.search(r"[\u4e00-\u9fff\u3400-\u4dbf\U0001f300-\U0001faff]", v))
    if not need:
        need = v.lower() in ("true","false","null","yes","no","on","off")
    return ("'" + v.replace("'","''") + "'") if need else v

def proxy_to_inline(p: dict) -> str:
    parts = []
    for k, v in p.items():
        if isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, dict):
            inner = ", ".join(
                f"{ik}: {_q(iv) if isinstance(iv,str) else (str(iv).lower() if isinstance(iv,bool) else iv)}"
                for ik, iv in v.items()
            )
            parts.append(f"{k}: {{{inner}}}")
        else:
            parts.append(f"{k}: {_q(v)}")
    return "    - { " + ", ".join(parts) + " }"

def group_to_inline(g: dict) -> str:
    name = _q(g["name"])
    plist = ", ".join(_q(x) for x in g.get("proxies", []))
    line = f"    - {{ name: {name}, type: {g['type']}, proxies: [{plist}]"
    if "url"      in g: line += f", url: {_q(g['url'])}"
    if "interval" in g: line += f", interval: {g['interval']}"
    if "tolerance"in g: line += f", tolerance: {g['tolerance']}"
    return line + " }"


# ── Build YAML đầy đủ từ danh sách proxy ────────────────────────────────────
INFO_VLESS_PREFIX = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:1?type=tcp#"

def build_yaml(proxy_list: list, is_liangxin: bool) -> str:
    """Nhận proxy list (đã rename), build YAML đầy đủ."""
    dns_block = LIANGXIN_DNS if is_liangxin else DJJC_DNS

    # Info nodes (fake vless)
    info_proxies = []
    for name in INFO_NODES:
        info_proxies.append({
            "name": name, "type": "vless",
            "server": "127.0.0.1", "port": 1,
            "uuid": "00000000-0000-0000-0000-000000000000",
            "udp": False, "tls": False, "skip-cert-verify": True,
        })

    all_proxies = info_proxies + proxy_list
    all_names = [p["name"] for p in all_proxies]
    real_names = [p["name"] for p in proxy_list]

    groups = [
        {"name": "VPN Trinh Hg", "type": "select",
         "proxies": ["Auto Select", "Fallback"] + all_names},
        {"name": "Auto Select", "type": "url-test",
         "proxies": real_names,
         "url": "http://www.gstatic.com/generate_204",
         "interval": 86400, "tolerance": 50},
        {"name": "Fallback", "type": "fallback",
         "proxies": real_names,
         "url": "http://www.gstatic.com/generate_204",
         "interval": 7200},
    ]

    lines = [
        "mixed-port: 7890", "allow-lan: false", "bind-address: '*'",
        "mode: rule", "log-level: info",
        "external-controller: '127.0.0.1:9090'",
        "unified-delay: true", "tcp-concurrent: true",
        dns_block,
        "proxies:",
    ]
    for p in all_proxies:
        lines.append(proxy_to_inline(p))
    lines.append("proxy-groups:")
    for g in groups:
        lines.append(group_to_inline(g))
    lines.append("rules:")
    for r in FULL_RULES:
        lines.append(f"    - {_q(r)}")

    result = "\n".join(lines)

    # Verify
    try:
        parsed = yaml.safe_load(result)
        pnames = {p["name"] for p in parsed.get("proxies", [])}
        gnames = {g["name"] for g in parsed.get("proxy-groups", [])}
        all_n  = pnames | gnames
        errs = [
            ref for g in parsed.get("proxy-groups", [])
            for ref in g.get("proxies", []) if ref not in all_n
        ]
        if errs:
            print(f"  [WARN] YAML verify errors: {errs[:3]}")
        else:
            print(f"  [OK] YAML ✅ ({len(pnames)} proxies, {len(gnames)} groups)")
    except Exception as e:
        print(f"  [WARN] YAML parse fail: {e}")

    return result


# ── Process b64: decode → rename → build new b64 + yaml ────────────────────
def process_b64(raw_b64: str, is_liangxin: bool):
    pad = raw_b64 + "=" * ((-len(raw_b64)) % 4)
    try:
        decoded = base64.b64decode(pad).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [!] b64 decode error: {e}")
        return raw_b64, ""

    lines = [l.strip() for l in decoded.splitlines() if l.strip() and "://" in l]
    rename_map = RENAME_LIANGXIN if is_liangxin else RENAME_DJJC

    new_b64_lines = []
    # 4 info nodes đầu tiên
    for name in INFO_NODES:
        new_b64_lines.append(INFO_VLESS_PREFIX + urllib.parse.quote(name, safe=""))

    proxy_list = []
    for line in lines:
        # Bỏ info/fake nodes (127.0.0.1 port 1)
        if "127.0.0.1" in line:
            continue
        if "://" not in line:
            continue

        old_name = None
        if "#" in line:
            old_name = urllib.parse.unquote(line.split("#", 1)[-1])

        # Bỏ info nodes gốc tiếng Trung
        if old_name and any(kw in old_name for kw in INFO_SKIP_KW):
            continue

        # Rename
        if old_name:
            new_name = rename_map.get(old_name)
            if new_name is None:
                # Nếu chưa có trong dict → giữ tên gốc + suffix nếu chưa có
                if "VPN Trinh Hg" not in old_name:
                    new_name = old_name + " - VPN Trinh Hg"
                else:
                    new_name = old_name
        else:
            new_name = old_name

        # Build URI mới với tên đã rename
        uri_base = line.split("#")[0]
        new_line = uri_base + "#" + urllib.parse.quote(new_name or "", safe="")
        new_b64_lines.append(new_line)

        # Parse proxy để build YAML
        proxy = uri_to_proxy(new_line)
        if proxy:
            proxy_list.append(proxy)

    # Build new b64
    new_b64_str = "\n".join(new_b64_lines)
    new_b64 = base64.b64encode(new_b64_str.encode("utf-8")).decode("ascii")

    print(f"  Parsed {len(proxy_list)} real proxies from {len(lines)} lines")

    # Build YAML
    yaml_str = ""
    if proxy_list:
        yaml_str = build_yaml(proxy_list, is_liangxin)
    else:
        print("  [!] No real proxies parsed — YAML will be empty")

    return new_b64, yaml_str


# ── Parse traffic info ────────────────────────────────────────────────────────
def parse_traffic(header: str) -> dict:
    def gi(p):
        m = re.search(p, header or "")
        return int(m.group(1)) if m else 0

    up  = gi(r"upload=(\d+)")
    dn  = gi(r"download=(\d+)")
    tot = gi(r"total=(\d+)")
    exp = gi(r"expire=(\d+)")
    used_gb  = (up + dn) / 1_073_741_824
    total_gb = tot / 1_073_741_824
    pct = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
    exp_str = (datetime.datetime.fromtimestamp(exp).strftime("%d/%m/%Y")
               if exp > 0 else "Vĩnh viễn")
    return {
        "used":    f"{used_gb:.2f}",
        "total":   f"{total_gb:.2f}",
        "percent": pct,
        "expire":  exp_str,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def update_all():
    print("=== VPN Trinh Hg — update_sub.py ===")
    try:
        res = requests.get(API_LINKS, timeout=15)
        res.raise_for_status()
        links_db = res.json()
    except Exception as e:
        print(f"[!] Lấy links thất bại: {e}")
        sys.exit(1)

    print(f"Tổng links: {len(links_db)}")

    # Lấy token gốc duy nhất (tránh fetch nhiều lần cùng link gốc)
    seen_orig = {}
    for lnk in links_db:
        orig = lnk.get("orig", "")
        if not orig:
            continue
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(orig).query)
            tok_list = qs.get("OwO") or qs.get("token")
            if tok_list:
                orig_token = tok_list[0]
                if orig_token not in seen_orig:
                    seen_orig[orig_token] = orig
        except Exception:
            continue

    print(f"Link gốc cần fetch: {len(seen_orig)}")

    for orig_token, orig_url in seen_orig.items():
        is_liangxin = "liangxin" in orig_url
        provider = "Liangxin" if is_liangxin else "DJJC"
        print(f"\n→ [{provider}] token: {orig_token[:12]}... url: {orig_url[:55]}...")

        try:
            r = requests.get(
                orig_url,
                headers={"User-Agent": "v2rayN/6.23"},
                timeout=30,
            )
            if r.status_code != 200:
                print(f"  [!] HTTP {r.status_code}")
                continue

            raw_b64   = r.text.strip()
            user_info = r.headers.get("subscription-userinfo", "")
            print(f"  b64 length: {len(raw_b64)} chars")

            if len(raw_b64) < 100:
                print("  [!] b64 quá ngắn, bỏ qua")
                continue

            traffic = parse_traffic(user_info)

            # Process
            final_b64, final_yaml = process_b64(raw_b64, is_liangxin)

            # Verify b64
            try:
                base64.b64decode(final_b64 + "=" * ((-len(final_b64)) % 4))
                print(f"  [OK] b64 ({len(final_b64)} chars)")
            except Exception as e:
                print(f"  [WARN] b64 invalid: {e}, dùng raw")
                final_b64 = raw_b64

            # Push KV
            payload = {
                "key":       orig_token,
                "body_b64":  final_b64,
                "body_yaml": final_yaml,
                "info":      user_info,
                "traffic":   traffic,
            }
            push_res = requests.post(API_PUSH, json=payload, timeout=20)
            print(f"  [OK] Push → HTTP {push_res.status_code}")

        except Exception as e:
            import traceback
            print(f"  [!] Lỗi: {e}")
            traceback.print_exc()

    print("\n=== Hoàn thành ===")


if __name__ == "__main__":
    update_all()
