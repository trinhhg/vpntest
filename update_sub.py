# v2.2 - Full Singbox/Hiddify Config khớp sát config gốc + Batch Push
"""
update_sub.py — VPN Trinh Hg
GitHub Actions: Chạy 1 lần/ngày lúc 00:00 UTC
So sánh với config gốc Hiddify: selector, urltest, direct, block, dns-out,
inbounds (mixed+tun), route rules đầy đủ, experimental cache+clash_api
"""

import requests, base64, urllib.parse, re, datetime, yaml, json, sys, time

WORKER_DOMAIN  = "https://vpn-worker-test.doicucden.workers.dev"
API_LINKS      = f"{WORKER_DOMAIN}/api/links"
API_BATCH_PUSH = f"{WORKER_DOMAIN}/api/push_data_batch"

INFO_NODES = [
    "🇻🇳 Truy cập web bên dưới",
    "🇻🇳 Để xem thêm gói khác",
    "🌐 Website: vpntrinhhg.pages.dev",
    "📞 Zalo: 0917678211",
]
INFO_SKIP_KW = ["剩余流量", "距离下次重置", "套餐到期"]
INFO_VLESS_PREFIX = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:1?type=tcp#"

# ── DNS Clash ─────────────────────────────────────────────────────────────────
DJJC_DNS_CLASH = """\
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

LIANGXIN_DNS_CLASH = """\
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

# ── Rules Clash (full) ────────────────────────────────────────────────────────
LIANGXIN_RULES = [
    "IP-CIDR,1.1.1.1/32,VPN Trinh Hg,no-resolve","IP-CIDR,8.8.8.8/32,VPN Trinh Hg,no-resolve",
    "DOMAIN-SUFFIX,services.googleapis.cn,VPN Trinh Hg","DOMAIN-SUFFIX,xn--ngstr-lra8j.com,VPN Trinh Hg",
    "DOMAIN,safebrowsing.urlsec.qq.com,DIRECT","DOMAIN,safebrowsing.googleapis.com,DIRECT",
    "DOMAIN,developer.apple.com,VPN Trinh Hg","DOMAIN-SUFFIX,digicert.com,VPN Trinh Hg",
    "DOMAIN,ocsp.apple.com,VPN Trinh Hg","DOMAIN,ocsp.comodoca.com,VPN Trinh Hg",
    "DOMAIN,ocsp.usertrust.com,VPN Trinh Hg","DOMAIN,ocsp.sectigo.com,VPN Trinh Hg",
    "DOMAIN,ocsp.verisign.net,VPN Trinh Hg","DOMAIN-SUFFIX,apple-dns.net,VPN Trinh Hg",
    "DOMAIN,testflight.apple.com,VPN Trinh Hg","DOMAIN,sandbox.itunes.apple.com,VPN Trinh Hg",
    "DOMAIN,itunes.apple.com,VPN Trinh Hg","DOMAIN-SUFFIX,apps.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blobstore.apple.com,VPN Trinh Hg","DOMAIN,cvws.icloud-content.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mzstatic.com,DIRECT","DOMAIN-SUFFIX,itunes.apple.com,DIRECT",
    "DOMAIN-SUFFIX,icloud.com,DIRECT","DOMAIN-SUFFIX,icloud-content.com,DIRECT",
    "DOMAIN-SUFFIX,me.com,DIRECT","DOMAIN-SUFFIX,aaplimg.com,DIRECT",
    "DOMAIN-SUFFIX,cdn20.com,DIRECT","DOMAIN-SUFFIX,cdn-apple.com,DIRECT",
    "DOMAIN-SUFFIX,akadns.net,DIRECT","DOMAIN-SUFFIX,akamaiedge.net,DIRECT",
    "DOMAIN-SUFFIX,edgekey.net,DIRECT","DOMAIN-SUFFIX,mwcloudcdn.com,DIRECT",
    "DOMAIN-SUFFIX,mwcname.com,DIRECT","DOMAIN-SUFFIX,apple.com,DIRECT",
    "DOMAIN-SUFFIX,apple-cloudkit.com,DIRECT","DOMAIN-SUFFIX,apple-mapkit.com,DIRECT",
    "DOMAIN,cn.bing.com,DIRECT",
    "DOMAIN-SUFFIX,126.com,DIRECT","DOMAIN-SUFFIX,126.net,DIRECT","DOMAIN-SUFFIX,127.net,DIRECT",
    "DOMAIN-SUFFIX,163.com,DIRECT","DOMAIN-SUFFIX,360buyimg.com,DIRECT","DOMAIN-SUFFIX,36kr.com,DIRECT",
    "DOMAIN-SUFFIX,acfun.tv,DIRECT","DOMAIN-SUFFIX,air-matters.com,DIRECT","DOMAIN-SUFFIX,aixifan.com,DIRECT",
    "DOMAIN-KEYWORD,alicdn,DIRECT","DOMAIN-KEYWORD,alipay,DIRECT","DOMAIN-KEYWORD,taobao,DIRECT",
    "DOMAIN-SUFFIX,amap.com,DIRECT","DOMAIN-SUFFIX,autonavi.com,DIRECT","DOMAIN-KEYWORD,baidu,DIRECT",
    "DOMAIN-SUFFIX,bdimg.com,DIRECT","DOMAIN-SUFFIX,bdstatic.com,DIRECT",
    "DOMAIN-SUFFIX,bilibili.com,DIRECT","DOMAIN-SUFFIX,bilivideo.com,DIRECT",
    "DOMAIN-SUFFIX,caiyunapp.com,DIRECT","DOMAIN-SUFFIX,clouddn.com,DIRECT",
    "DOMAIN-SUFFIX,cnbeta.com,DIRECT","DOMAIN-SUFFIX,cnbetacdn.com,DIRECT",
    "DOMAIN-SUFFIX,cootekservice.com,DIRECT","DOMAIN-SUFFIX,csdn.net,DIRECT",
    "DOMAIN-SUFFIX,ctrip.com,DIRECT","DOMAIN-SUFFIX,dgtle.com,DIRECT",
    "DOMAIN-SUFFIX,dianping.com,DIRECT","DOMAIN-SUFFIX,douban.com,DIRECT",
    "DOMAIN-SUFFIX,doubanio.com,DIRECT","DOMAIN-SUFFIX,duokan.com,DIRECT",
    "DOMAIN-SUFFIX,easou.com,DIRECT","DOMAIN-SUFFIX,ele.me,DIRECT",
    "DOMAIN-SUFFIX,feng.com,DIRECT","DOMAIN-SUFFIX,fir.im,DIRECT",
    "DOMAIN-SUFFIX,frdic.com,DIRECT","DOMAIN-SUFFIX,g-cores.com,DIRECT",
    "DOMAIN-SUFFIX,godic.net,DIRECT","DOMAIN-SUFFIX,gtimg.com,DIRECT",
    "DOMAIN,cdn.hockeyapp.net,DIRECT","DOMAIN-SUFFIX,hongxiu.com,DIRECT",
    "DOMAIN-SUFFIX,hxcdn.net,DIRECT","DOMAIN-SUFFIX,iciba.com,DIRECT",
    "DOMAIN-SUFFIX,ifeng.com,DIRECT","DOMAIN-SUFFIX,ifengimg.com,DIRECT",
    "DOMAIN-SUFFIX,ipip.net,DIRECT","DOMAIN-SUFFIX,iqiyi.com,DIRECT",
    "DOMAIN-SUFFIX,jd.com,DIRECT","DOMAIN-SUFFIX,jianshu.com,DIRECT",
    "DOMAIN-SUFFIX,knewone.com,DIRECT","DOMAIN-SUFFIX,le.com,DIRECT",
    "DOMAIN-SUFFIX,lecloud.com,DIRECT","DOMAIN-SUFFIX,lemicp.com,DIRECT",
    "DOMAIN-SUFFIX,licdn.com,DIRECT","DOMAIN-SUFFIX,luoo.net,DIRECT",
    "DOMAIN-SUFFIX,meituan.com,DIRECT","DOMAIN-SUFFIX,meituan.net,DIRECT",
    "DOMAIN-SUFFIX,mi.com,DIRECT","DOMAIN-SUFFIX,miaopai.com,DIRECT",
    "DOMAIN-SUFFIX,microsoft.com,DIRECT","DOMAIN-SUFFIX,microsoftonline.com,DIRECT",
    "DOMAIN-SUFFIX,miui.com,DIRECT","DOMAIN-SUFFIX,miwifi.com,DIRECT",
    "DOMAIN-SUFFIX,mob.com,DIRECT","DOMAIN-SUFFIX,netease.com,DIRECT",
    "DOMAIN-SUFFIX,office.com,DIRECT","DOMAIN-SUFFIX,office365.com,DIRECT",
    "DOMAIN-KEYWORD,officecdn,DIRECT","DOMAIN-SUFFIX,oschina.net,DIRECT",
    "DOMAIN-SUFFIX,ppsimg.com,DIRECT","DOMAIN-SUFFIX,pstatp.com,DIRECT",
    "DOMAIN-SUFFIX,qcloud.com,DIRECT","DOMAIN-SUFFIX,qdaily.com,DIRECT",
    "DOMAIN-SUFFIX,qdmm.com,DIRECT","DOMAIN-SUFFIX,qhimg.com,DIRECT",
    "DOMAIN-SUFFIX,qhres.com,DIRECT","DOMAIN-SUFFIX,qidian.com,DIRECT",
    "DOMAIN-SUFFIX,qihucdn.com,DIRECT","DOMAIN-SUFFIX,qiniu.com,DIRECT",
    "DOMAIN-SUFFIX,qiniucdn.com,DIRECT","DOMAIN-SUFFIX,qiyipic.com,DIRECT",
    "DOMAIN-SUFFIX,qq.com,DIRECT","DOMAIN-SUFFIX,qqurl.com,DIRECT",
    "DOMAIN-SUFFIX,rarbg.to,DIRECT","DOMAIN-SUFFIX,ruguoapp.com,DIRECT",
    "DOMAIN-SUFFIX,segmentfault.com,DIRECT","DOMAIN-SUFFIX,sinaapp.com,DIRECT",
    "DOMAIN-SUFFIX,smzdm.com,DIRECT","DOMAIN-SUFFIX,snapdrop.net,DIRECT",
    "DOMAIN-SUFFIX,sogou.com,DIRECT","DOMAIN-SUFFIX,sogoucdn.com,DIRECT",
    "DOMAIN-SUFFIX,sohu.com,DIRECT","DOMAIN-SUFFIX,soku.com,DIRECT",
    "DOMAIN-SUFFIX,speedtest.net,DIRECT","DOMAIN-SUFFIX,sspai.com,DIRECT",
    "DOMAIN-SUFFIX,suning.com,DIRECT","DOMAIN-SUFFIX,taobao.com,DIRECT",
    "DOMAIN-SUFFIX,tencent.com,DIRECT","DOMAIN-SUFFIX,tenpay.com,DIRECT",
    "DOMAIN-SUFFIX,tianyancha.com,DIRECT","DOMAIN-SUFFIX,tmall.com,DIRECT",
    "DOMAIN-SUFFIX,tudou.com,DIRECT","DOMAIN-SUFFIX,umetrip.com,DIRECT",
    "DOMAIN-SUFFIX,upaiyun.com,DIRECT","DOMAIN-SUFFIX,upyun.com,DIRECT",
    "DOMAIN-SUFFIX,veryzhun.com,DIRECT","DOMAIN-SUFFIX,weather.com,DIRECT",
    "DOMAIN-SUFFIX,weibo.com,DIRECT","DOMAIN-SUFFIX,xiami.com,DIRECT",
    "DOMAIN-SUFFIX,xiami.net,DIRECT","DOMAIN-SUFFIX,xiaomicp.com,DIRECT",
    "DOMAIN-SUFFIX,ximalaya.com,DIRECT","DOMAIN-SUFFIX,xmcdn.com,DIRECT",
    "DOMAIN-SUFFIX,xunlei.com,DIRECT","DOMAIN-SUFFIX,yhd.com,DIRECT",
    "DOMAIN-SUFFIX,yihaodianimg.com,DIRECT","DOMAIN-SUFFIX,yinxiang.com,DIRECT",
    "DOMAIN-SUFFIX,ykimg.com,DIRECT","DOMAIN-SUFFIX,youdao.com,DIRECT",
    "DOMAIN-SUFFIX,youku.com,DIRECT","DOMAIN-SUFFIX,zealer.com,DIRECT",
    "DOMAIN-SUFFIX,zhihu.com,DIRECT","DOMAIN-SUFFIX,zhimg.com,DIRECT",
    "DOMAIN-SUFFIX,zimuzu.tv,DIRECT","DOMAIN-SUFFIX,zoho.com,DIRECT",
    "DOMAIN-KEYWORD,amazon,VPN Trinh Hg","DOMAIN-KEYWORD,google,VPN Trinh Hg",
    "DOMAIN-KEYWORD,gmail,VPN Trinh Hg","DOMAIN-KEYWORD,youtube,VPN Trinh Hg",
    "DOMAIN-KEYWORD,facebook,VPN Trinh Hg","DOMAIN-SUFFIX,fb.me,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fbcdn.net,VPN Trinh Hg","DOMAIN-KEYWORD,twitter,VPN Trinh Hg",
    "DOMAIN-KEYWORD,instagram,VPN Trinh Hg","DOMAIN-KEYWORD,dropbox,VPN Trinh Hg",
    "DOMAIN-SUFFIX,twimg.com,VPN Trinh Hg","DOMAIN-KEYWORD,blogspot,VPN Trinh Hg",
    "DOMAIN-SUFFIX,youtu.be,VPN Trinh Hg","DOMAIN-KEYWORD,whatsapp,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegra.ph,VPN Trinh Hg","DOMAIN-SUFFIX,telegram.org,VPN Trinh Hg",
    "DOMAIN-KEYWORD,admarvel,REJECT","DOMAIN-KEYWORD,admaster,REJECT",
    "DOMAIN-KEYWORD,adsage,REJECT","DOMAIN-KEYWORD,adsmogo,REJECT",
    "DOMAIN-KEYWORD,adsrvmedia,REJECT","DOMAIN-KEYWORD,adwords,REJECT",
    "DOMAIN-KEYWORD,adservice,REJECT","DOMAIN-SUFFIX,appsflyer.com,REJECT",
    "DOMAIN-KEYWORD,domob,REJECT","DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-KEYWORD,duomeng,REJECT","DOMAIN-KEYWORD,dwtrack,REJECT",
    "DOMAIN-KEYWORD,guanggao,REJECT","DOMAIN-KEYWORD,lianmeng,REJECT",
    "DOMAIN-SUFFIX,mmstat.com,REJECT","DOMAIN-KEYWORD,mopub,REJECT",
    "DOMAIN-KEYWORD,omgmta,REJECT","DOMAIN-KEYWORD,openx,REJECT",
    "DOMAIN-KEYWORD,partnerad,REJECT","DOMAIN-KEYWORD,pingfore,REJECT",
    "DOMAIN-KEYWORD,supersonicads,REJECT","DOMAIN-KEYWORD,uedas,REJECT",
    "DOMAIN-KEYWORD,umeng,REJECT","DOMAIN-KEYWORD,usage,REJECT",
    "DOMAIN-SUFFIX,vungle.com,REJECT","DOMAIN-KEYWORD,wlmonitor,REJECT",
    "DOMAIN-KEYWORD,zjtoolbar,REJECT",
    "DOMAIN-SUFFIX,9to5mac.com,VPN Trinh Hg","DOMAIN-SUFFIX,abpchina.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,adblockplus.org,VPN Trinh Hg","DOMAIN-SUFFIX,adobe.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,akamaized.net,VPN Trinh Hg","DOMAIN-SUFFIX,android.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appspot.com,VPN Trinh Hg","DOMAIN-SUFFIX,archive.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,awsstatic.com,VPN Trinh Hg","DOMAIN-SUFFIX,azureedge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,azurewebsites.net,VPN Trinh Hg","DOMAIN-SUFFIX,bing.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bit.ly,VPN Trinh Hg","DOMAIN-SUFFIX,bitbucket.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogger.com,VPN Trinh Hg","DOMAIN-SUFFIX,blogspot.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bloomberg.com,VPN Trinh Hg","DOMAIN-SUFFIX,box.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cachefly.net,VPN Trinh Hg","DOMAIN-SUFFIX,chromium.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudflare.com,VPN Trinh Hg","DOMAIN-SUFFIX,cloudfront.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,docker.com,VPN Trinh Hg","DOMAIN-SUFFIX,dribbble.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,duckduckgo.com,VPN Trinh Hg","DOMAIN-SUFFIX,evernote.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fast.com,VPN Trinh Hg","DOMAIN-SUFFIX,fastly.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedly.com,VPN Trinh Hg","DOMAIN-SUFFIX,firebaseio.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flickr.com,VPN Trinh Hg","DOMAIN-SUFFIX,g.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ggpht.com,VPN Trinh Hg","DOMAIN-SUFFIX,git.io,VPN Trinh Hg",
    "DOMAIN-KEYWORD,github,VPN Trinh Hg","DOMAIN-SUFFIX,golang.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goo.gl,VPN Trinh Hg","DOMAIN-SUFFIX,goodreads.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gravatar.com,VPN Trinh Hg","DOMAIN-SUFFIX,gstatic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,hotmail.com,VPN Trinh Hg","DOMAIN-SUFFIX,imgur.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,instapaper.com,VPN Trinh Hg","DOMAIN-SUFFIX,linkedin.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,live.com,VPN Trinh Hg","DOMAIN-SUFFIX,live.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,medium.com,VPN Trinh Hg","DOMAIN-SUFFIX,mega.nz,VPN Trinh Hg",
    "DOMAIN-SUFFIX,microsofttranslator.com,VPN Trinh Hg","DOMAIN-SUFFIX,msedge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,onedrive.com,VPN Trinh Hg","DOMAIN-SUFFIX,onenote.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,openvpn.net,VPN Trinh Hg","DOMAIN-SUFFIX,outlook.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pinterest.com,VPN Trinh Hg","DOMAIN-SUFFIX,pixiv.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.com,VPN Trinh Hg","DOMAIN-SUFFIX,playstation.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,shadowsocks.org,VPN Trinh Hg","DOMAIN-SUFFIX,skype.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,soundcloud.com,VPN Trinh Hg","DOMAIN-SUFFIX,sourceforge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,spotify.com,VPN Trinh Hg","DOMAIN-SUFFIX,stackoverflow.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,steamcommunity.com,VPN Trinh Hg","DOMAIN-SUFFIX,techcrunch.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,theverge.com,VPN Trinh Hg","DOMAIN-SUFFIX,todoist.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,trello.com,VPN Trinh Hg","DOMAIN-SUFFIX,tumblr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,twitch.tv,VPN Trinh Hg","DOMAIN-SUFFIX,v2ex.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vimeo.com,VPN Trinh Hg","DOMAIN-SUFFIX,vultr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,w.org,VPN Trinh Hg","DOMAIN-SUFFIX,wikipedia.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,windows.com,VPN Trinh Hg","DOMAIN-SUFFIX,windows.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wordpress.com,VPN Trinh Hg","DOMAIN-SUFFIX,wsj.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yahoo.com,VPN Trinh Hg","DOMAIN-SUFFIX,ytimg.com,VPN Trinh Hg",
    "IP-CIDR,91.108.4.0/22,VPN Trinh Hg,no-resolve","IP-CIDR,91.108.8.0/21,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.16.0/22,VPN Trinh Hg,no-resolve","IP-CIDR,91.108.56.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,149.154.160.0/20,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:67c:4e8::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23d::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23f::/48,VPN Trinh Hg,no-resolve",
    "DOMAIN,injections.adguard.org,DIRECT","DOMAIN,local.adguard.org,DIRECT",
    "DOMAIN-SUFFIX,local,DIRECT","IP-CIDR,127.0.0.0/8,DIRECT",
    "IP-CIDR,172.16.0.0/12,DIRECT","IP-CIDR,192.168.0.0/16,DIRECT",
    "IP-CIDR,10.0.0.0/8,DIRECT","IP-CIDR,100.64.0.0/10,DIRECT",
    "IP-CIDR,224.0.0.0/4,DIRECT","IP-CIDR6,fe80::/10,DIRECT",
    "DOMAIN-SUFFIX,cn,DIRECT","DOMAIN-KEYWORD,-cn,DIRECT",
    "GEOIP,CN,DIRECT","MATCH,VPN Trinh Hg"
]

DJJC_RULES = [r for r in LIANGXIN_RULES if not r.startswith("IP-CIDR,1.1.1.1") and not r.startswith("IP-CIDR,8.8.8.8") and "cn.bing.com" not in r]


# ── Parse proxy URI ───────────────────────────────────────────────────────────
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
    if "://" not in line: return None
    proto = line.split("://")[0].lower()
    name = urllib.parse.unquote(line.split("#", 1)[-1]) if "#" in line else None
    proxy = None
    if proto in ("hysteria2", "hy2"):   proxy = parse_hysteria2(line)
    elif proto == "vless":              proxy = parse_vless(line)
    elif proto == "trojan":             proxy = parse_trojan(line)
    if proxy and name: proxy["name"] = name
    return proxy if (proxy and proxy.get("name") and proxy.get("server")) else None


# ── Singbox outbound converter ────────────────────────────────────────────────
def proxy_to_singbox_outbound(p: dict) -> dict | None:
    """Chuyển proxy dict → singbox outbound, khớp sát format config gốc Hiddify"""
    out = {
        "type": p["type"],
        "tag":  p["name"],
        "server": p["server"],
        "server_port": int(p["port"])
    }
    if p["type"] == "vless":
        out["uuid"] = p.get("uuid", "")
        out["packet_encoding"] = "xudp"
        if p.get("flow"):
            out["flow"] = p["flow"]
        if p.get("tls"):
            tls = {"enabled": True}
            if p.get("servername"):
                tls["server_name"] = p["servername"]
            if p.get("client-fingerprint"):
                tls["utls"] = {"enabled": True, "fingerprint": p["client-fingerprint"]}
            if p.get("skip-cert-verify"):
                tls["insecure"] = True
            if p.get("reality-opts"):
                tls["reality"] = {
                    "enabled":    True,
                    "public_key": p["reality-opts"].get("public-key", ""),
                    "short_id":   p["reality-opts"].get("short-id", "")
                }
            out["tls"] = tls
        if p.get("network") == "ws":
            out["transport"] = {
                "type":    "ws",
                "path":    p["ws-opts"].get("path", "/"),
                "headers": p["ws-opts"].get("headers", {}),
                "max_early_data": 2048,
                "early_data_header_name": "Sec-WebSocket-Protocol"
            }
        elif p.get("network") == "grpc":
            out["transport"] = {
                "type":         "grpc",
                "service_name": p["grpc-opts"].get("grpc-service-name", "")
            }

    elif p["type"] in ("hysteria2", "hy2"):
        out["type"]     = "hysteria2"
        out["password"] = p.get("password", "")
        tls = {"enabled": True}
        if p.get("sni"):              tls["server_name"] = p["sni"]
        if p.get("skip-cert-verify"): tls["insecure"]    = True
        out["tls"] = tls

    elif p["type"] == "trojan":
        out["password"] = p.get("password", "")
        tls = {"enabled": True}
        if p.get("sni"):              tls["server_name"] = p["sni"]
        if p.get("skip-cert-verify"): tls["insecure"]    = True
        out["tls"] = tls
    else:
        return None
    return out


# ── Build Singbox FULL CONFIG (khớp sát Hiddify) ─────────────────────────────
def build_singbox_full(proxy_list: list, is_liangxin: bool) -> str:
    """
    Output JSON khớp sát với config gốc xuất từ Hiddify:
    selector → urltest → direct → block → dns-out → info nodes → real nodes
    + inbounds (mixed + tun) + dns block + route rules + experimental
    """
    real_names   = [p["name"] for p in proxy_list]
    active_rules = LIANGXIN_RULES if is_liangxin else DJJC_RULES
    proxy_group  = "节点选择"

    # ── Outbounds — thứ tự giống hệt file gốc ─────────────────────────────
    outbounds = []

    # 1. selector (giống gốc: default = 自动选择)
    outbounds.append({
        "type":     "selector",
        "tag":      proxy_group,
        "outbounds": ["自动选择"] + real_names,
        "default":  "自动选择"
    })

    # 2. urltest (interval "1m0s", idle_timeout "30m0s" — khớp gốc)
    outbounds.append({
        "type":         "urltest",
        "tag":          "自动选择",
        "outbounds":    real_names,
        "url":          "https://www.gstatic.com/generate_204",
        "interval":     "1m0s",
        "tolerance":    50,
        "idle_timeout": "30m0s"
    })

    # 3. direct, block, dns-out
    outbounds.append({"type": "direct", "tag": "direct"})
    outbounds.append({"type": "block",  "tag": "block"})
    outbounds.append({"type": "dns",    "tag": "dns-out"})

    # 4. Info nodes (fake vless 127.0.0.1:1)
    for i, name in enumerate(INFO_NODES):
        outbounds.append({
            "type":            "vless",
            "tag":             f"{name} § {i}",
            "server":          "127.0.0.1",
            "server_port":     1,
            "uuid":            "00000000-0000-0000-0000-000000000000",
            "packet_encoding": "xudp"
        })

    # 5. Real proxies
    for p in proxy_list:
        ob = proxy_to_singbox_outbound(p)
        if ob: outbounds.append(ob)

    # ── DNS block ──────────────────────────────────────────────────────────
    dns_block = {
        "servers": [
            {
                "tag":     "proxy-dns",
                "address": "https://8.8.8.8/dns-query",
                "detour":  proxy_group
            },
            {
                "tag":     "direct-dns",
                "address": "https://223.5.5.5/dns-query",
                "detour":  "direct"
            },
            {
                "tag":     "block-dns",
                "address": "rcode://success"
            }
        ],
        "rules": [
            {"outbound": "any",    "server": "direct-dns"},
            {"clash_mode": "Direct", "server": "direct-dns"},
            {"clash_mode": "Global", "server": "proxy-dns"},
            {"rule_set": ["geosite-cn"], "server": "direct-dns"},
            {"rule_set": ["geosite-category-ads-all"], "server": "block-dns"}
        ],
        "final":            "proxy-dns",
        "independent_cache": True
    }

    # ── Inbounds ───────────────────────────────────────────────────────────
    inbounds = [
        {
            "type":                       "mixed",
            "tag":                        "mixed-in",
            "listen":                     "127.0.0.1",
            "listen_port":                2080,
            "sniff":                      True,
            "sniff_override_destination": True
        },
        {
            "type":                       "tun",
            "tag":                        "tun-in",
            "inet4_address":              "172.19.0.1/30",
            "inet6_address":              "fdfe:dcba:9876::1/126",
            "mtu":                        9000,
            "auto_route":                 True,
            "strict_route":               True,
            "sniff":                      True,
            "sniff_override_destination": True,
            "domain_strategy":            "prefer_ipv4"
        }
    ]

    # ── Route rules — gom nhóm theo outbound ──────────────────────────────
    dir_d, dir_s, dir_k, dir_ip, dir_geo = [], [], [], [], []
    prx_d, prx_s, prx_k, prx_ip         = [], [], [], []
    blk_d, blk_s, blk_k                 = [], [], []

    for rule_str in active_rules:
        parts = rule_str.strip().split(",")
        if len(parts) < 3: continue
        rtype, value, target = parts[0], parts[1], parts[2]
        is_dir = target == "DIRECT"
        is_blk = target in ("REJECT", "REJECT-DROP")
        is_prx = not is_dir and not is_blk

        if   rtype == "DOMAIN":         (dir_d  if is_dir else blk_d  if is_blk else prx_d).append(value)
        elif rtype == "DOMAIN-SUFFIX":  (dir_s  if is_dir else blk_s  if is_blk else prx_s).append(value)
        elif rtype == "DOMAIN-KEYWORD": (dir_k  if is_dir else blk_k  if is_blk else prx_k).append(value)
        elif rtype in ("IP-CIDR","IP-CIDR6"):
            (dir_ip if is_dir else prx_ip).append(value)
        elif rtype == "GEOIP":
            if is_dir: dir_geo.append(value.lower())

    route_rules = [
        {"protocol": "dns", "outbound": "dns-out"}
    ]
    if blk_d or blk_s or blk_k:
        r = {"outbound": "block"}
        if blk_d: r["domain"]         = blk_d
        if blk_s: r["domain_suffix"]  = blk_s
        if blk_k: r["domain_keyword"] = blk_k
        route_rules.append(r)
    if dir_d or dir_s or dir_k:
        r = {"outbound": "direct"}
        if dir_d: r["domain"]         = dir_d
        if dir_s: r["domain_suffix"]  = dir_s
        if dir_k: r["domain_keyword"] = dir_k
        route_rules.append(r)
    if dir_ip:  route_rules.append({"ip_cidr": dir_ip, "outbound": "direct"})
    if dir_geo: route_rules.append({"geoip":   dir_geo, "outbound": "direct"})
    if prx_d or prx_s or prx_k:
        r = {"outbound": proxy_group}
        if prx_d: r["domain"]         = prx_d
        if prx_s: r["domain_suffix"]  = prx_s
        if prx_k: r["domain_keyword"] = prx_k
        route_rules.append(r)
    if prx_ip: route_rules.append({"ip_cidr": prx_ip, "outbound": proxy_group})
    route_rules.append({"geoip": ["cn"], "outbound": "direct"})

    route_block = {
        "rules":                 route_rules,
        "final":                 proxy_group,
        "auto_detect_interface": True,
        "override_android_vpn":  True
    }

    full_config = {
        "log":      {"level": "info", "timestamp": True},
        "dns":      dns_block,
        "inbounds": inbounds,
        "outbounds": outbounds,
        "route":    route_block,
        "experimental": {
            "cache_file": {
                "enabled":       True,
                "path":          "cache.db",
                "store_fakeip":  True
            },
            "clash_api": {
                "external_controller": "127.0.0.1:9090",
                "external_ui":         "ui",
                "secret":              ""
            }
        }
    }
    return json.dumps(full_config, ensure_ascii=False, indent=2)


# ── YAML helpers ──────────────────────────────────────────────────────────────
def _q(v) -> str:
    if isinstance(v, bool): return str(v).lower()
    if not isinstance(v, str): return str(v)
    need = any(c in v for c in ':{}[]|>&*!,#\'"%-?@`') or v[0:1] in "!&*?|-" or " " in v
    if not need: need = bool(re.search(r"[\u4e00-\u9fff\u3400-\u4dbf\U0001f300-\U0001faff]", v))
    if not need: need = v.lower() in ("true","false","null","yes","no","on","off")
    return ("'" + v.replace("'","''") + "'") if need else v

def proxy_to_inline(p: dict) -> str:
    parts = []
    for k, v in p.items():
        if isinstance(v, bool):   parts.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, dict):
            inner = ", ".join(f"{ik}: {_q(iv) if isinstance(iv,str) else (str(iv).lower() if isinstance(iv,bool) else iv)}" for ik, iv in v.items())
            parts.append(f"{k}: {{{inner}}}")
        else: parts.append(f"{k}: {_q(v)}")
    return "    - { " + ", ".join(parts) + " }"

def group_to_inline(g: dict) -> str:
    name  = _q(g["name"])
    plist = ", ".join(_q(x) for x in g.get("proxies", []))
    line  = f"    - {{ name: {name}, type: {g['type']}, proxies: [{plist}]"
    if "url"      in g: line += f", url: {_q(g['url'])}"
    if "interval" in g: line += f", interval: {g['interval']}"
    if "tolerance" in g: line += f", tolerance: {g['tolerance']}"
    return line + " }"

def build_yaml(proxy_list: list, is_liangxin: bool) -> str:
    dns_clash  = LIANGXIN_DNS_CLASH if is_liangxin else DJJC_DNS_CLASH
    rules_list = LIANGXIN_RULES     if is_liangxin else DJJC_RULES

    info_proxies = []
    for name in INFO_NODES:
        info_proxies.append({
            "name": name, "type": "vless",
            "server": "127.0.0.1", "port": 1,
            "uuid": "00000000-0000-0000-0000-000000000000",
            "udp": False, "tls": False, "skip-cert-verify": True,
        })

    all_proxies = info_proxies + proxy_list
    all_names   = [p["name"] for p in all_proxies]
    real_names  = [p["name"] for p in proxy_list]

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
        dns_clash, "proxies:",
    ]
    for p in all_proxies:  lines.append(proxy_to_inline(p))
    lines.append("proxy-groups:")
    for g in groups:       lines.append(group_to_inline(g))
    lines.append("rules:")
    for r in rules_list:   lines.append(f"    - {_q(r)}")

    result = "\n".join(lines)
    try:
        parsed = yaml.safe_load(result)
        pnames = {p["name"] for p in parsed.get("proxies", [])}
        gnames = {g["name"] for g in parsed.get("proxy-groups", [])}
        all_n  = pnames | gnames
        errs   = [ref for g in parsed.get("proxy-groups",[]) for ref in g.get("proxies",[]) if ref not in all_n]
        if errs:  print(f"  [WARN] YAML verify errors: {errs[:3]}")
        else:     print(f"  [OK] YAML ✅ ({len(pnames)} proxies, {len(gnames)} groups)")
    except Exception as e:
        print(f"  [WARN] YAML parse fail: {e}")
    return result


# ── Process b64 ───────────────────────────────────────────────────────────────
def process_b64(raw_b64: str, is_liangxin: bool):
    pad = raw_b64 + "=" * ((-len(raw_b64)) % 4)
    try:
        decoded = base64.b64decode(pad).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [!] b64 decode error: {e}"); return raw_b64, "", ""

    lines = [l.strip() for l in decoded.splitlines() if l.strip() and "://" in l]
    new_b64_lines = [INFO_VLESS_PREFIX + urllib.parse.quote(n, safe="") for n in INFO_NODES]
    proxy_list = []

    for line in lines:
        if "127.0.0.1" in line or "://" not in line: continue
        old_name = urllib.parse.unquote(line.split("#", 1)[-1]) if "#" in line else None
        if old_name and any(kw in old_name for kw in INFO_SKIP_KW): continue
        if old_name:
            new_name = old_name if "VPNTrinhHg" in old_name else old_name + " - VPNTrinhHg"
        else:
            new_name = old_name
        uri_base = line.split("#")[0]
        new_line = uri_base + "#" + urllib.parse.quote(new_name or "", safe="")
        new_b64_lines.append(new_line)
        proxy = uri_to_proxy(new_line)
        if proxy: proxy_list.append(proxy)

    new_b64 = base64.b64encode("\n".join(new_b64_lines).encode("utf-8")).decode("ascii")
    print(f"  Parsed {len(proxy_list)} real proxies from {len(lines)} lines")

    yaml_str    = build_yaml(proxy_list, is_liangxin)        if proxy_list else ""
    singbox_str = build_singbox_full(proxy_list, is_liangxin) if proxy_list else ""
    return new_b64, yaml_str, singbox_str


# ── Parse traffic ─────────────────────────────────────────────────────────────
def parse_traffic(header: str) -> dict:
    def gi(p): m = re.search(p, header or ""); return int(m.group(1)) if m else 0
    up, dn, tot, exp = gi(r"upload=(\d+)"), gi(r"download=(\d+)"), gi(r"total=(\d+)"), gi(r"expire=(\d+)")
    used_gb  = (up + dn) / 1_073_741_824
    total_gb = tot       / 1_073_741_824
    pct      = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
    exp_str  = datetime.datetime.fromtimestamp(exp).strftime("%d/%m/%Y") if exp > 0 else "Vĩnh viễn"
    return {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": pct, "expire": exp_str}


# ── Main ──────────────────────────────────────────────────────────────────────
def update_all():
    print("=== VPN Trinh Hg — update_sub.py v2.2 ===")
    try:
        res = requests.get(API_LINKS, timeout=15); res.raise_for_status()
        links_db = res.json()
    except Exception as e:
        print(f"[!] Lấy links thất bại: {e}"); sys.exit(1)

    print(f"Tổng links: {len(links_db)}")
    seen_orig = {}
    for lnk in links_db:
        orig = lnk.get("orig", "")
        if not orig: continue
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(orig).query)
            tok_list = qs.get("OwO") or qs.get("token")
            if tok_list:
                t = tok_list[0]
                if t not in seen_orig: seen_orig[t] = orig
        except Exception: continue

    print(f"Link gốc cần fetch: {len(seen_orig)}")
    global_subs_payload = {}

    for orig_token, orig_url in seen_orig.items():
        is_liangxin = "liangxin" in orig_url
        provider    = "Liangxin" if is_liangxin else "DJJC"
        print(f"\n→ [{provider}] token: {orig_token[:12]}... url: {orig_url[:55]}...")
        try:
            r = requests.get(orig_url, headers={"User-Agent": "v2rayN/6.23",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}, timeout=30)
            if r.status_code != 200:
                print(f"  [!] HTTP {r.status_code}"); time.sleep(3); continue
            raw_b64   = r.text.strip()
            user_info = r.headers.get("subscription-userinfo", "")
            print(f"  b64 length: {len(raw_b64)} chars")
            if len(raw_b64) < 1000 or "ERROR" in raw_b64:
                print("  [!] Bỏ qua - b64 quá ngắn hoặc lỗi"); time.sleep(3); continue
            traffic = parse_traffic(user_info)
            final_b64, final_yaml, final_singbox = process_b64(raw_b64, is_liangxin)
            try:
                base64.b64decode(final_b64 + "=" * ((-len(final_b64)) % 4))
                print(f"  [OK] b64 ({len(final_b64)} chars)")
            except Exception as e:
                print(f"  [WARN] b64 invalid: {e}, dùng raw"); final_b64 = raw_b64
            global_subs_payload[orig_token] = {
                "body_b64": final_b64, "body_yaml": final_yaml,
                "body_singbox": final_singbox, "info": user_info, "traffic": traffic,
            }
        except Exception as e:
            import traceback; print(f"  [!] Lỗi: {e}"); traceback.print_exc()
        time.sleep(3)

    if global_subs_payload:
        print(f"\n[+] Đang đẩy BATCH {len(global_subs_payload)} links lên KV...")
        try:
            push_res = requests.post(API_BATCH_PUSH, json=global_subs_payload, timeout=30)
            print(f"  [OK] Batch Push → HTTP {push_res.status_code}")
        except Exception as e: print(f"  [!] Lỗi Batch Push: {e}")
    else:
        print("\n[!] Không có data nào hợp lệ để push.")
    print("\n=== Hoàn thành ===")

if __name__ == "__main__":
    update_all()
