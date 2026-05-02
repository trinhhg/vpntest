# v1.1 - Tách riêng 2 bộ rules và DNS cho Liangxin và DJJC - 2026-05-03
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

# ── Rules riêng biệt ─────────────────────────────────────────────────────────
DJJC_RULES = [
    "DOMAIN-SUFFIX,services.googleapis.cn,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xn--ngstr-lra8j.com,VPN Trinh Hg",
    "DOMAIN,safebrowsing.urlsec.qq.com,DIRECT",
    "DOMAIN,safebrowsing.googleapis.com,DIRECT",
    "DOMAIN,developer.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,digicert.com,VPN Trinh Hg",
    "DOMAIN,ocsp.apple.com,VPN Trinh Hg",
    "DOMAIN,ocsp.comodoca.com,VPN Trinh Hg",
    "DOMAIN,ocsp.usertrust.com,VPN Trinh Hg",
    "DOMAIN,ocsp.sectigo.com,VPN Trinh Hg",
    "DOMAIN,ocsp.verisign.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apple-dns.net,VPN Trinh Hg",
    "DOMAIN,testflight.apple.com,VPN Trinh Hg",
    "DOMAIN,sandbox.itunes.apple.com,VPN Trinh Hg",
    "DOMAIN,itunes.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apps.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blobstore.apple.com,VPN Trinh Hg",
    "DOMAIN,cvws.icloud-content.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mzstatic.com,DIRECT",
    "DOMAIN-SUFFIX,itunes.apple.com,DIRECT",
    "DOMAIN-SUFFIX,icloud.com,DIRECT",
    "DOMAIN-SUFFIX,icloud-content.com,DIRECT",
    "DOMAIN-SUFFIX,me.com,DIRECT",
    "DOMAIN-SUFFIX,aaplimg.com,DIRECT",
    "DOMAIN-SUFFIX,cdn20.com,DIRECT",
    "DOMAIN-SUFFIX,cdn-apple.com,DIRECT",
    "DOMAIN-SUFFIX,akadns.net,DIRECT",
    "DOMAIN-SUFFIX,akamaiedge.net,DIRECT",
    "DOMAIN-SUFFIX,edgekey.net,DIRECT",
    "DOMAIN-SUFFIX,mwcloudcdn.com,DIRECT",
    "DOMAIN-SUFFIX,mwcname.com,DIRECT",
    "DOMAIN-SUFFIX,apple.com,DIRECT",
    "DOMAIN-SUFFIX,apple-cloudkit.com,DIRECT",
    "DOMAIN-SUFFIX,apple-mapkit.com,DIRECT",
    "DOMAIN-SUFFIX,126.com,DIRECT",
    "DOMAIN-SUFFIX,126.net,DIRECT",
    "DOMAIN-SUFFIX,127.net,DIRECT",
    "DOMAIN-SUFFIX,163.com,DIRECT",
    "DOMAIN-SUFFIX,360buyimg.com,DIRECT",
    "DOMAIN-SUFFIX,36kr.com,DIRECT",
    "DOMAIN-SUFFIX,acfun.tv,DIRECT",
    "DOMAIN-SUFFIX,air-matters.com,DIRECT",
    "DOMAIN-SUFFIX,aixifan.com,DIRECT",
    "DOMAIN-KEYWORD,alicdn,DIRECT",
    "DOMAIN-KEYWORD,alipay,DIRECT",
    "DOMAIN-KEYWORD,taobao,DIRECT",
    "DOMAIN-SUFFIX,amap.com,DIRECT",
    "DOMAIN-SUFFIX,autonavi.com,DIRECT",
    "DOMAIN-KEYWORD,baidu,DIRECT",
    "DOMAIN-SUFFIX,bdimg.com,DIRECT",
    "DOMAIN-SUFFIX,bdstatic.com,DIRECT",
    "DOMAIN-SUFFIX,bilibili.com,DIRECT",
    "DOMAIN-SUFFIX,bilivideo.com,DIRECT",
    "DOMAIN-SUFFIX,caiyunapp.com,DIRECT",
    "DOMAIN-SUFFIX,clouddn.com,DIRECT",
    "DOMAIN-SUFFIX,cnbeta.com,DIRECT",
    "DOMAIN-SUFFIX,cnbetacdn.com,DIRECT",
    "DOMAIN-SUFFIX,cootekservice.com,DIRECT",
    "DOMAIN-SUFFIX,csdn.net,DIRECT",
    "DOMAIN-SUFFIX,ctrip.com,DIRECT",
    "DOMAIN-SUFFIX,dgtle.com,DIRECT",
    "DOMAIN-SUFFIX,dianping.com,DIRECT",
    "DOMAIN-SUFFIX,douban.com,DIRECT",
    "DOMAIN-SUFFIX,doubanio.com,DIRECT",
    "DOMAIN-SUFFIX,duokan.com,DIRECT",
    "DOMAIN-SUFFIX,easou.com,DIRECT",
    "DOMAIN-SUFFIX,ele.me,DIRECT",
    "DOMAIN-SUFFIX,feng.com,DIRECT",
    "DOMAIN-SUFFIX,fir.im,DIRECT",
    "DOMAIN-SUFFIX,frdic.com,DIRECT",
    "DOMAIN-SUFFIX,g-cores.com,DIRECT",
    "DOMAIN-SUFFIX,godic.net,DIRECT",
    "DOMAIN-SUFFIX,gtimg.com,DIRECT",
    "DOMAIN,cdn.hockeyapp.net,DIRECT",
    "DOMAIN-SUFFIX,hongxiu.com,DIRECT",
    "DOMAIN-SUFFIX,hxcdn.net,DIRECT",
    "DOMAIN-SUFFIX,iciba.com,DIRECT",
    "DOMAIN-SUFFIX,ifeng.com,DIRECT",
    "DOMAIN-SUFFIX,ifengimg.com,DIRECT",
    "DOMAIN-SUFFIX,ipip.net,DIRECT",
    "DOMAIN-SUFFIX,iqiyi.com,DIRECT",
    "DOMAIN-SUFFIX,jd.com,DIRECT",
    "DOMAIN-SUFFIX,jianshu.com,DIRECT",
    "DOMAIN-SUFFIX,knewone.com,DIRECT",
    "DOMAIN-SUFFIX,le.com,DIRECT",
    "DOMAIN-SUFFIX,lecloud.com,DIRECT",
    "DOMAIN-SUFFIX,lemicp.com,DIRECT",
    "DOMAIN-SUFFIX,licdn.com,DIRECT",
    "DOMAIN-SUFFIX,luoo.net,DIRECT",
    "DOMAIN-SUFFIX,meituan.com,DIRECT",
    "DOMAIN-SUFFIX,meituan.net,DIRECT",
    "DOMAIN-SUFFIX,mi.com,DIRECT",
    "DOMAIN-SUFFIX,miaopai.com,DIRECT",
    "DOMAIN-SUFFIX,microsoft.com,DIRECT",
    "DOMAIN-SUFFIX,microsoftonline.com,DIRECT",
    "DOMAIN-SUFFIX,miui.com,DIRECT",
    "DOMAIN-SUFFIX,miwifi.com,DIRECT",
    "DOMAIN-SUFFIX,mob.com,DIRECT",
    "DOMAIN-SUFFIX,netease.com,DIRECT",
    "DOMAIN-SUFFIX,office.com,DIRECT",
    "DOMAIN-SUFFIX,office365.com,DIRECT",
    "DOMAIN-KEYWORD,officecdn,DIRECT",
    "DOMAIN-SUFFIX,oschina.net,DIRECT",
    "DOMAIN-SUFFIX,ppsimg.com,DIRECT",
    "DOMAIN-SUFFIX,pstatp.com,DIRECT",
    "DOMAIN-SUFFIX,qcloud.com,DIRECT",
    "DOMAIN-SUFFIX,qdaily.com,DIRECT",
    "DOMAIN-SUFFIX,qdmm.com,DIRECT",
    "DOMAIN-SUFFIX,qhimg.com,DIRECT",
    "DOMAIN-SUFFIX,qhres.com,DIRECT",
    "DOMAIN-SUFFIX,qidian.com,DIRECT",
    "DOMAIN-SUFFIX,qihucdn.com,DIRECT",
    "DOMAIN-SUFFIX,qiniu.com,DIRECT",
    "DOMAIN-SUFFIX,qiniucdn.com,DIRECT",
    "DOMAIN-SUFFIX,qiyipic.com,DIRECT",
    "DOMAIN-SUFFIX,qq.com,DIRECT",
    "DOMAIN-SUFFIX,qqurl.com,DIRECT",
    "DOMAIN-SUFFIX,rarbg.to,DIRECT",
    "DOMAIN-SUFFIX,ruguoapp.com,DIRECT",
    "DOMAIN-SUFFIX,segmentfault.com,DIRECT",
    "DOMAIN-SUFFIX,sinaapp.com,DIRECT",
    "DOMAIN-SUFFIX,smzdm.com,DIRECT",
    "DOMAIN-SUFFIX,snapdrop.net,DIRECT",
    "DOMAIN-SUFFIX,sogou.com,DIRECT",
    "DOMAIN-SUFFIX,sogoucdn.com,DIRECT",
    "DOMAIN-SUFFIX,sohu.com,DIRECT",
    "DOMAIN-SUFFIX,soku.com,DIRECT",
    "DOMAIN-SUFFIX,speedtest.net,DIRECT",
    "DOMAIN-SUFFIX,sspai.com,DIRECT",
    "DOMAIN-SUFFIX,suning.com,DIRECT",
    "DOMAIN-SUFFIX,taobao.com,DIRECT",
    "DOMAIN-SUFFIX,tencent.com,DIRECT",
    "DOMAIN-SUFFIX,tenpay.com,DIRECT",
    "DOMAIN-SUFFIX,tianyancha.com,DIRECT",
    "DOMAIN-SUFFIX,tmall.com,DIRECT",
    "DOMAIN-SUFFIX,tudou.com,DIRECT",
    "DOMAIN-SUFFIX,umetrip.com,DIRECT",
    "DOMAIN-SUFFIX,upaiyun.com,DIRECT",
    "DOMAIN-SUFFIX,upyun.com,DIRECT",
    "DOMAIN-SUFFIX,veryzhun.com,DIRECT",
    "DOMAIN-SUFFIX,weather.com,DIRECT",
    "DOMAIN-SUFFIX,weibo.com,DIRECT",
    "DOMAIN-SUFFIX,xiami.com,DIRECT",
    "DOMAIN-SUFFIX,xiami.net,DIRECT",
    "DOMAIN-SUFFIX,xiaomicp.com,DIRECT",
    "DOMAIN-SUFFIX,ximalaya.com,DIRECT",
    "DOMAIN-SUFFIX,xmcdn.com,DIRECT",
    "DOMAIN-SUFFIX,xunlei.com,DIRECT",
    "DOMAIN-SUFFIX,yhd.com,DIRECT",
    "DOMAIN-SUFFIX,yihaodianimg.com,DIRECT",
    "DOMAIN-SUFFIX,yinxiang.com,DIRECT",
    "DOMAIN-SUFFIX,ykimg.com,DIRECT",
    "DOMAIN-SUFFIX,youdao.com,DIRECT",
    "DOMAIN-SUFFIX,youku.com,DIRECT",
    "DOMAIN-SUFFIX,zealer.com,DIRECT",
    "DOMAIN-SUFFIX,zhihu.com,DIRECT",
    "DOMAIN-SUFFIX,zhimg.com,DIRECT",
    "DOMAIN-SUFFIX,zimuzu.tv,DIRECT",
    "DOMAIN-SUFFIX,zoho.com,DIRECT",
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
    "DOMAIN-KEYWORD,admarvel,REJECT",
    "DOMAIN-KEYWORD,admaster,REJECT",
    "DOMAIN-KEYWORD,adsage,REJECT",
    "DOMAIN-KEYWORD,adsmogo,REJECT",
    "DOMAIN-KEYWORD,adsrvmedia,REJECT",
    "DOMAIN-KEYWORD,adwords,REJECT",
    "DOMAIN-KEYWORD,adservice,REJECT",
    "DOMAIN-SUFFIX,appsflyer.com,REJECT",
    "DOMAIN-KEYWORD,domob,REJECT",
    "DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-KEYWORD,duomeng,REJECT",
    "DOMAIN-KEYWORD,dwtrack,REJECT",
    "DOMAIN-KEYWORD,guanggao,REJECT",
    "DOMAIN-KEYWORD,lianmeng,REJECT",
    "DOMAIN-SUFFIX,mmstat.com,REJECT",
    "DOMAIN-KEYWORD,mopub,REJECT",
    "DOMAIN-KEYWORD,omgmta,REJECT",
    "DOMAIN-KEYWORD,openx,REJECT",
    "DOMAIN-KEYWORD,partnerad,REJECT",
    "DOMAIN-KEYWORD,pingfore,REJECT",
    "DOMAIN-KEYWORD,supersonicads,REJECT",
    "DOMAIN-KEYWORD,uedas,REJECT",
    "DOMAIN-KEYWORD,umeng,REJECT",
    "DOMAIN-KEYWORD,usage,REJECT",
    "DOMAIN-SUFFIX,vungle.com,REJECT",
    "DOMAIN-KEYWORD,wlmonitor,REJECT",
    "DOMAIN-KEYWORD,zjtoolbar,REJECT",
    "DOMAIN-SUFFIX,9to5mac.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,abpchina.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,adblockplus.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,adobe.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,akamaized.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,alfredapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,amplitude.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ampproject.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,android.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,angularjs.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,aolcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apkpure.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appledaily.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appshopper.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appspot.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,arcgis.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,archive.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,armorgames.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,aspnetcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,att.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,awsstatic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,azureedge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,azurewebsites.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bing.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bintray.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bit.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bit.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bitbucket.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bjango.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bkrtx.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blog.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogger.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogsmithmedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogspot.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogspot.hk,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bloomberg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,box.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,box.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cachefly.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,chromium.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cl.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudflare.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudfront.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudmagic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cmail19.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cnet.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cocoapods.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,comodoca.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,crashlytics.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,culturedcode.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,d.pr,VPN Trinh Hg",
    "DOMAIN-SUFFIX,danilo.to,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dayone.me,VPN Trinh Hg",
    "DOMAIN-SUFFIX,db.tt,VPN Trinh Hg",
    "DOMAIN-SUFFIX,deskconnect.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,disq.us,VPN Trinh Hg",
    "DOMAIN-SUFFIX,disqus.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,disquscdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dnsimple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,docker.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dribbble.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,droplr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,duckduckgo.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dueapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dytt8.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,edgecastcdn.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,edgekey.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,edgesuite.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,engadget.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,entrust.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,eurekavpt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,evernote.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fabric.io,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fast.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fastly.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fc2.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedburner.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedly.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedsportal.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fiftythree.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,firebaseio.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flexibits.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flickr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flipboard.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,g.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gabia.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,geni.us,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gfx.ms,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ggpht.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ghostnoteapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,git.io,VPN Trinh Hg",
    "DOMAIN-KEYWORD,github,VPN Trinh Hg",
    "DOMAIN-SUFFIX,globalsign.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gmodules.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,godaddy.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,golang.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gongm.in,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goo.gl,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goodreaders.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goodreads.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gravatar.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gstatic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gvt0.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,hockeyapp.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,hotmail.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,icons8.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ifixit.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ift.tt,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ifttt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,iherb.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,imageshack.us,VPN Trinh Hg",
    "DOMAIN-SUFFIX,img.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,imgur.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,imore.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,instapaper.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ipn.li,VPN Trinh Hg",
    "DOMAIN-SUFFIX,is.gd,VPN Trinh Hg",
    "DOMAIN-SUFFIX,issuu.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,itgonglun.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,itun.es,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ixquick.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,j.mp,VPN Trinh Hg",
    "DOMAIN-SUFFIX,js.revsci.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,jshint.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,jtvnw.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,justgetflux.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,kat.cr,VPN Trinh Hg",
    "DOMAIN-SUFFIX,klip.me,VPN Trinh Hg",
    "DOMAIN-SUFFIX,libsyn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,linkedin.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,line-apps.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,linode.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,lithium.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,littlehj.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,live.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,live.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,livefilestore.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,llnwd.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,macid.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,macromedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,macrumors.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mashable.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mathjax.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,medium.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mega.co.nz,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mega.nz,VPN Trinh Hg",
    "DOMAIN-SUFFIX,megaupload.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,microsofttranslator.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mindnode.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mobile01.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,modmyi.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,msedge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,myfontastic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,name.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nextmedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nsstatic.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nssurge.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nyt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nytimes.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,omnigroup.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,onedrive.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,onenote.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ooyala.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,openvpn.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,openwrt.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,orkut.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,osxdaily.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,outlook.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ow.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,paddleapi.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,parallels.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,parse.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pdfexpert.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,periscope.tv,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pinboard.in,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pinterest.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pixelmator.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pixiv.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playpcesor.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.com.hk,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstationnetwork.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pushwoosh.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,rime.im,VPN Trinh Hg",
    "DOMAIN-SUFFIX,servebom.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sfx.ms,VPN Trinh Hg",
    "DOMAIN-SUFFIX,shadowsocks.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sharethis.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,shazam.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,skype.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,smartdnsVPN Trinh Hg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,smartmailcloud.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sndcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sony.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,soundcloud.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sourceforge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,spotify.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,squarespace.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sstatic.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,st.luluku.pw,VPN Trinh Hg",
    "DOMAIN-SUFFIX,stackoverflow.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,startpage.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,staticflickr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,steamcommunity.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,symauth.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,symcb.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,symcd.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tapbots.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tapbots.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tdesktop.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,techcrunch.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,techsmith.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,thepiratebay.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,theverge.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,time.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,timeinc.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tiny.cc,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tinypic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tmblr.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,todoist.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,trello.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,trustasiassl.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tumblr.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tumblr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tweetdeck.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tweetmarker.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,twitch.tv,VPN Trinh Hg",
    "DOMAIN-SUFFIX,txmblr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,typekit.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ubertags.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ublock.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ubnt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ulyssesapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,urchin.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,usertrust.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,v.gd,VPN Trinh Hg",
    "DOMAIN-SUFFIX,v2ex.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vimeo.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vimeocdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vine.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vivaldi.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vox-cdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vsco.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vultr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,w.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,w3schools.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,webtype.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikiwand.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikileaks.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikimedia.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikipedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikipedia.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,windows.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,windows.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wire.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wordpress.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,workflowy.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wsj.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wsj.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xda-developers.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xeeno.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xiti.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yahoo.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yimg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ying.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yoyo.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ytimg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegra.ph,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegram.org,VPN Trinh Hg",
    "IP-CIDR,91.108.4.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.8.0/21,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.16.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.56.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,149.154.160.0/20,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:67c:4e8::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23d::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23f::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.232.181.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.241.147.226/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.253.226/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.255.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.255.34/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.255.98/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.150.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.150.34/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.151.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.151.34/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.39.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.40.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.41.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.43.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.50.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,220.181.174.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,220.181.174.226/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,220.181.174.34/32,VPN Trinh Hg,no-resolve",
    "DOMAIN,injections.adguard.org,DIRECT",
    "DOMAIN,local.adguard.org,DIRECT",
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
    "MATCH,VPN Trinh Hg"
]

LIANGXIN_RULES = [
    "IP-CIDR,1.1.1.1/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,8.8.8.8/32,VPN Trinh Hg,no-resolve",
    "DOMAIN-SUFFIX,services.googleapis.cn,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xn--ngstr-lra8j.com,VPN Trinh Hg",
    "DOMAIN,safebrowsing.urlsec.qq.com,DIRECT",
    "DOMAIN,safebrowsing.googleapis.com,DIRECT",
    "DOMAIN,developer.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,digicert.com,VPN Trinh Hg",
    "DOMAIN,ocsp.apple.com,VPN Trinh Hg",
    "DOMAIN,ocsp.comodoca.com,VPN Trinh Hg",
    "DOMAIN,ocsp.usertrust.com,VPN Trinh Hg",
    "DOMAIN,ocsp.sectigo.com,VPN Trinh Hg",
    "DOMAIN,ocsp.verisign.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apple-dns.net,VPN Trinh Hg",
    "DOMAIN,testflight.apple.com,VPN Trinh Hg",
    "DOMAIN,sandbox.itunes.apple.com,VPN Trinh Hg",
    "DOMAIN,itunes.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apps.apple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blobstore.apple.com,VPN Trinh Hg",
    "DOMAIN,cvws.icloud-content.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mzstatic.com,DIRECT",
    "DOMAIN-SUFFIX,itunes.apple.com,DIRECT",
    "DOMAIN-SUFFIX,icloud.com,DIRECT",
    "DOMAIN-SUFFIX,icloud-content.com,DIRECT",
    "DOMAIN-SUFFIX,me.com,DIRECT",
    "DOMAIN-SUFFIX,aaplimg.com,DIRECT",
    "DOMAIN-SUFFIX,cdn20.com,DIRECT",
    "DOMAIN-SUFFIX,cdn-apple.com,DIRECT",
    "DOMAIN-SUFFIX,akadns.net,DIRECT",
    "DOMAIN-SUFFIX,akamaiedge.net,DIRECT",
    "DOMAIN-SUFFIX,edgekey.net,DIRECT",
    "DOMAIN-SUFFIX,mwcloudcdn.com,DIRECT",
    "DOMAIN-SUFFIX,mwcname.com,DIRECT",
    "DOMAIN-SUFFIX,apple.com,DIRECT",
    "DOMAIN-SUFFIX,apple-cloudkit.com,DIRECT",
    "DOMAIN-SUFFIX,apple-mapkit.com,DIRECT",
    "DOMAIN,cn.bing.com,DIRECT",
    "DOMAIN-SUFFIX,126.com,DIRECT",
    "DOMAIN-SUFFIX,126.net,DIRECT",
    "DOMAIN-SUFFIX,127.net,DIRECT",
    "DOMAIN-SUFFIX,163.com,DIRECT",
    "DOMAIN-SUFFIX,360buyimg.com,DIRECT",
    "DOMAIN-SUFFIX,36kr.com,DIRECT",
    "DOMAIN-SUFFIX,acfun.tv,DIRECT",
    "DOMAIN-SUFFIX,air-matters.com,DIRECT",
    "DOMAIN-SUFFIX,aixifan.com,DIRECT",
    "DOMAIN-KEYWORD,alicdn,DIRECT",
    "DOMAIN-KEYWORD,alipay,DIRECT",
    "DOMAIN-KEYWORD,taobao,DIRECT",
    "DOMAIN-SUFFIX,amap.com,DIRECT",
    "DOMAIN-SUFFIX,autonavi.com,DIRECT",
    "DOMAIN-KEYWORD,baidu,DIRECT",
    "DOMAIN-SUFFIX,bdimg.com,DIRECT",
    "DOMAIN-SUFFIX,bdstatic.com,DIRECT",
    "DOMAIN-SUFFIX,bilibili.com,DIRECT",
    "DOMAIN-SUFFIX,bilivideo.com,DIRECT",
    "DOMAIN-SUFFIX,caiyunapp.com,DIRECT",
    "DOMAIN-SUFFIX,clouddn.com,DIRECT",
    "DOMAIN-SUFFIX,cnbeta.com,DIRECT",
    "DOMAIN-SUFFIX,cnbetacdn.com,DIRECT",
    "DOMAIN-SUFFIX,cootekservice.com,DIRECT",
    "DOMAIN-SUFFIX,csdn.net,DIRECT",
    "DOMAIN-SUFFIX,ctrip.com,DIRECT",
    "DOMAIN-SUFFIX,dgtle.com,DIRECT",
    "DOMAIN-SUFFIX,dianping.com,DIRECT",
    "DOMAIN-SUFFIX,douban.com,DIRECT",
    "DOMAIN-SUFFIX,doubanio.com,DIRECT",
    "DOMAIN-SUFFIX,duokan.com,DIRECT",
    "DOMAIN-SUFFIX,easou.com,DIRECT",
    "DOMAIN-SUFFIX,ele.me,DIRECT",
    "DOMAIN-SUFFIX,feng.com,DIRECT",
    "DOMAIN-SUFFIX,fir.im,DIRECT",
    "DOMAIN-SUFFIX,frdic.com,DIRECT",
    "DOMAIN-SUFFIX,g-cores.com,DIRECT",
    "DOMAIN-SUFFIX,godic.net,DIRECT",
    "DOMAIN-SUFFIX,gtimg.com,DIRECT",
    "DOMAIN,cdn.hockeyapp.net,DIRECT",
    "DOMAIN-SUFFIX,hongxiu.com,DIRECT",
    "DOMAIN-SUFFIX,hxcdn.net,DIRECT",
    "DOMAIN-SUFFIX,iciba.com,DIRECT",
    "DOMAIN-SUFFIX,ifeng.com,DIRECT",
    "DOMAIN-SUFFIX,ifengimg.com,DIRECT",
    "DOMAIN-SUFFIX,ipip.net,DIRECT",
    "DOMAIN-SUFFIX,iqiyi.com,DIRECT",
    "DOMAIN-SUFFIX,jd.com,DIRECT",
    "DOMAIN-SUFFIX,jianshu.com,DIRECT",
    "DOMAIN-SUFFIX,knewone.com,DIRECT",
    "DOMAIN-SUFFIX,le.com,DIRECT",
    "DOMAIN-SUFFIX,lecloud.com,DIRECT",
    "DOMAIN-SUFFIX,lemicp.com,DIRECT",
    "DOMAIN-SUFFIX,licdn.com,DIRECT",
    "DOMAIN-SUFFIX,luoo.net,DIRECT",
    "DOMAIN-SUFFIX,meituan.com,DIRECT",
    "DOMAIN-SUFFIX,meituan.net,DIRECT",
    "DOMAIN-SUFFIX,mi.com,DIRECT",
    "DOMAIN-SUFFIX,miaopai.com,DIRECT",
    "DOMAIN-SUFFIX,microsoft.com,DIRECT",
    "DOMAIN-SUFFIX,microsoftonline.com,DIRECT",
    "DOMAIN-SUFFIX,miui.com,DIRECT",
    "DOMAIN-SUFFIX,miwifi.com,DIRECT",
    "DOMAIN-SUFFIX,mob.com,DIRECT",
    "DOMAIN-SUFFIX,netease.com,DIRECT",
    "DOMAIN-SUFFIX,office.com,DIRECT",
    "DOMAIN-SUFFIX,office365.com,DIRECT",
    "DOMAIN-KEYWORD,officecdn,DIRECT",
    "DOMAIN-SUFFIX,oschina.net,DIRECT",
    "DOMAIN-SUFFIX,ppsimg.com,DIRECT",
    "DOMAIN-SUFFIX,pstatp.com,DIRECT",
    "DOMAIN-SUFFIX,qcloud.com,DIRECT",
    "DOMAIN-SUFFIX,qdaily.com,DIRECT",
    "DOMAIN-SUFFIX,qdmm.com,DIRECT",
    "DOMAIN-SUFFIX,qhimg.com,DIRECT",
    "DOMAIN-SUFFIX,qhres.com,DIRECT",
    "DOMAIN-SUFFIX,qidian.com,DIRECT",
    "DOMAIN-SUFFIX,qihucdn.com,DIRECT",
    "DOMAIN-SUFFIX,qiniu.com,DIRECT",
    "DOMAIN-SUFFIX,qiniucdn.com,DIRECT",
    "DOMAIN-SUFFIX,qiyipic.com,DIRECT",
    "DOMAIN-SUFFIX,qq.com,DIRECT",
    "DOMAIN-SUFFIX,qqurl.com,DIRECT",
    "DOMAIN-SUFFIX,rarbg.to,DIRECT",
    "DOMAIN-SUFFIX,ruguoapp.com,DIRECT",
    "DOMAIN-SUFFIX,segmentfault.com,DIRECT",
    "DOMAIN-SUFFIX,sinaapp.com,DIRECT",
    "DOMAIN-SUFFIX,smzdm.com,DIRECT",
    "DOMAIN-SUFFIX,snapdrop.net,DIRECT",
    "DOMAIN-SUFFIX,sogou.com,DIRECT",
    "DOMAIN-SUFFIX,sogoucdn.com,DIRECT",
    "DOMAIN-SUFFIX,sohu.com,DIRECT",
    "DOMAIN-SUFFIX,soku.com,DIRECT",
    "DOMAIN-SUFFIX,speedtest.net,DIRECT",
    "DOMAIN-SUFFIX,sspai.com,DIRECT",
    "DOMAIN-SUFFIX,suning.com,DIRECT",
    "DOMAIN-SUFFIX,taobao.com,DIRECT",
    "DOMAIN-SUFFIX,tencent.com,DIRECT",
    "DOMAIN-SUFFIX,tenpay.com,DIRECT",
    "DOMAIN-SUFFIX,tianyancha.com,DIRECT",
    "DOMAIN-SUFFIX,tmall.com,DIRECT",
    "DOMAIN-SUFFIX,tudou.com,DIRECT",
    "DOMAIN-SUFFIX,umetrip.com,DIRECT",
    "DOMAIN-SUFFIX,upaiyun.com,DIRECT",
    "DOMAIN-SUFFIX,upyun.com,DIRECT",
    "DOMAIN-SUFFIX,veryzhun.com,DIRECT",
    "DOMAIN-SUFFIX,weather.com,DIRECT",
    "DOMAIN-SUFFIX,weibo.com,DIRECT",
    "DOMAIN-SUFFIX,xiami.com,DIRECT",
    "DOMAIN-SUFFIX,xiami.net,DIRECT",
    "DOMAIN-SUFFIX,xiaomicp.com,DIRECT",
    "DOMAIN-SUFFIX,ximalaya.com,DIRECT",
    "DOMAIN-SUFFIX,xmcdn.com,DIRECT",
    "DOMAIN-SUFFIX,xunlei.com,DIRECT",
    "DOMAIN-SUFFIX,yhd.com,DIRECT",
    "DOMAIN-SUFFIX,yihaodianimg.com,DIRECT",
    "DOMAIN-SUFFIX,yinxiang.com,DIRECT",
    "DOMAIN-SUFFIX,ykimg.com,DIRECT",
    "DOMAIN-SUFFIX,youdao.com,DIRECT",
    "DOMAIN-SUFFIX,youku.com,DIRECT",
    "DOMAIN-SUFFIX,zealer.com,DIRECT",
    "DOMAIN-SUFFIX,zhihu.com,DIRECT",
    "DOMAIN-SUFFIX,zhimg.com,DIRECT",
    "DOMAIN-SUFFIX,zimuzu.tv,DIRECT",
    "DOMAIN-SUFFIX,zoho.com,DIRECT",
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
    "DOMAIN-KEYWORD,admarvel,REJECT",
    "DOMAIN-KEYWORD,admaster,REJECT",
    "DOMAIN-KEYWORD,adsage,REJECT",
    "DOMAIN-KEYWORD,adsmogo,REJECT",
    "DOMAIN-KEYWORD,adsrvmedia,REJECT",
    "DOMAIN-KEYWORD,adwords,REJECT",
    "DOMAIN-KEYWORD,adservice,REJECT",
    "DOMAIN-SUFFIX,appsflyer.com,REJECT",
    "DOMAIN-KEYWORD,domob,REJECT",
    "DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-KEYWORD,duomeng,REJECT",
    "DOMAIN-KEYWORD,dwtrack,REJECT",
    "DOMAIN-KEYWORD,guanggao,REJECT",
    "DOMAIN-KEYWORD,lianmeng,REJECT",
    "DOMAIN-SUFFIX,mmstat.com,REJECT",
    "DOMAIN-KEYWORD,mopub,REJECT",
    "DOMAIN-KEYWORD,omgmta,REJECT",
    "DOMAIN-KEYWORD,openx,REJECT",
    "DOMAIN-KEYWORD,partnerad,REJECT",
    "DOMAIN-KEYWORD,pingfore,REJECT",
    "DOMAIN-KEYWORD,supersonicads,REJECT",
    "DOMAIN-KEYWORD,uedas,REJECT",
    "DOMAIN-KEYWORD,umeng,REJECT",
    "DOMAIN-KEYWORD,usage,REJECT",
    "DOMAIN-SUFFIX,vungle.com,REJECT",
    "DOMAIN-KEYWORD,wlmonitor,REJECT",
    "DOMAIN-KEYWORD,zjtoolbar,REJECT",
    "DOMAIN-SUFFIX,9to5mac.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,abpchina.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,adblockplus.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,adobe.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,akamaized.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,alfredapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,amplitude.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ampproject.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,android.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,angularjs.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,aolcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,apkpure.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appledaily.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appshopper.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,appspot.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,arcgis.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,archive.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,armorgames.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,aspnetcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,att.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,awsstatic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,azureedge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,azurewebsites.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bing.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bintray.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bit.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bit.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bitbucket.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bjango.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bkrtx.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blog.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogger.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogsmithmedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogspot.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,blogspot.hk,VPN Trinh Hg",
    "DOMAIN-SUFFIX,bloomberg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,box.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,box.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cachefly.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,chromium.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cl.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudflare.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudfront.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cloudmagic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cmail19.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cnet.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,cocoapods.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,comodoca.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,crashlytics.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,culturedcode.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,d.pr,VPN Trinh Hg",
    "DOMAIN-SUFFIX,danilo.to,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dayone.me,VPN Trinh Hg",
    "DOMAIN-SUFFIX,db.tt,VPN Trinh Hg",
    "DOMAIN-SUFFIX,deskconnect.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,disq.us,VPN Trinh Hg",
    "DOMAIN-SUFFIX,disqus.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,disquscdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dnsimple.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,docker.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dribbble.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,droplr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,duckduckgo.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dueapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,dytt8.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,edgecastcdn.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,edgekey.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,edgesuite.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,engadget.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,entrust.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,eurekavpt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,evernote.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fabric.io,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fast.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fastly.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fc2.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedburner.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedly.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,feedsportal.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,fiftythree.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,firebaseio.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flexibits.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flickr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,flipboard.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,g.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gabia.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,geni.us,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gfx.ms,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ggpht.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ghostnoteapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,git.io,VPN Trinh Hg",
    "DOMAIN-KEYWORD,github,VPN Trinh Hg",
    "DOMAIN-SUFFIX,globalsign.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gmodules.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,godaddy.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,golang.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gongm.in,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goo.gl,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goodreaders.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,goodreads.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gravatar.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gstatic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,gvt0.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,hockeyapp.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,hotmail.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,icons8.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ifixit.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ift.tt,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ifttt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,iherb.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,imageshack.us,VPN Trinh Hg",
    "DOMAIN-SUFFIX,img.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,imgur.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,imore.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,instapaper.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ipn.li,VPN Trinh Hg",
    "DOMAIN-SUFFIX,is.gd,VPN Trinh Hg",
    "DOMAIN-SUFFIX,issuu.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,itgonglun.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,itun.es,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ixquick.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,j.mp,VPN Trinh Hg",
    "DOMAIN-SUFFIX,js.revsci.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,jshint.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,jtvnw.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,justgetflux.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,kat.cr,VPN Trinh Hg",
    "DOMAIN-SUFFIX,klip.me,VPN Trinh Hg",
    "DOMAIN-SUFFIX,libsyn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,linkedin.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,line-apps.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,linode.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,lithium.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,littlehj.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,live.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,live.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,livefilestore.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,llnwd.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,macid.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,macromedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,macrumors.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mashable.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mathjax.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,medium.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mega.co.nz,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mega.nz,VPN Trinh Hg",
    "DOMAIN-SUFFIX,megaupload.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,microsofttranslator.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mindnode.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,mobile01.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,modmyi.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,msedge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,myfontastic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,name.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nextmedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nsstatic.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nssurge.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nyt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,nytimes.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,omnigroup.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,onedrive.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,onenote.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ooyala.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,openvpn.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,openwrt.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,orkut.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,osxdaily.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,outlook.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ow.ly,VPN Trinh Hg",
    "DOMAIN-SUFFIX,paddleapi.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,parallels.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,parse.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pdfexpert.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,periscope.tv,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pinboard.in,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pinterest.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pixelmator.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pixiv.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playpcesor.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.com.hk,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstation.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,playstationnetwork.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,pushwoosh.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,rime.im,VPN Trinh Hg",
    "DOMAIN-SUFFIX,servebom.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sfx.ms,VPN Trinh Hg",
    "DOMAIN-SUFFIX,shadowsocks.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sharethis.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,shazam.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,skype.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,smartdnsVPN Trinh Hg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,smartmailcloud.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sndcdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sony.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,soundcloud.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sourceforge.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,spotify.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,squarespace.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,sstatic.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,st.luluku.pw,VPN Trinh Hg",
    "DOMAIN-SUFFIX,stackoverflow.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,startpage.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,staticflickr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,steamcommunity.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,symauth.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,symcb.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,symcd.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tapbots.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tapbots.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tdesktop.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,techcrunch.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,techsmith.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,thepiratebay.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,theverge.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,time.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,timeinc.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tiny.cc,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tinypic.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tmblr.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,todoist.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,trello.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,trustasiassl.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tumblr.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tumblr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tweetdeck.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,tweetmarker.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,twitch.tv,VPN Trinh Hg",
    "DOMAIN-SUFFIX,txmblr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,typekit.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ubertags.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ublock.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ubnt.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ulyssesapp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,urchin.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,usertrust.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,v.gd,VPN Trinh Hg",
    "DOMAIN-SUFFIX,v2ex.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vimeo.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vimeocdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vine.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vivaldi.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vox-cdn.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vsco.co,VPN Trinh Hg",
    "DOMAIN-SUFFIX,vultr.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,w.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,w3schools.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,webtype.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikiwand.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikileaks.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikimedia.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikipedia.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wikipedia.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,windows.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,windows.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wire.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wordpress.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,workflowy.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wp.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wsj.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,wsj.net,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xda-developers.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xeeno.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,xiti.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yahoo.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yimg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ying.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,yoyo.org,VPN Trinh Hg",
    "DOMAIN-SUFFIX,ytimg.com,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegra.ph,VPN Trinh Hg",
    "DOMAIN-SUFFIX,telegram.org,VPN Trinh Hg",
    "IP-CIDR,91.108.4.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.8.0/21,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.16.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,91.108.56.0/22,VPN Trinh Hg,no-resolve",
    "IP-CIDR,149.154.160.0/20,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:67c:4e8::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23d::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR6,2001:b28:f23f::/48,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.232.181.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.241.147.226/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.253.226/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.255.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.255.34/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,120.253.255.98/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.150.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.150.34/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.151.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,180.163.151.34/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.39.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.40.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.41.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.43.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,203.208.50.0/24,VPN Trinh Hg,no-resolve",
    "IP-CIDR,220.181.174.162/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,220.181.174.226/32,VPN Trinh Hg,no-resolve",
    "IP-CIDR,220.181.174.34/32,VPN Trinh Hg,no-resolve",
    "DOMAIN,injections.adguard.org,DIRECT",
    "DOMAIN,local.adguard.org,DIRECT",
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
    "MATCH,VPN Trinh Hg"
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
    active_rules = LIANGXIN_RULES if is_liangxin else DJJC_RULES

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
    for r in active_rules:
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

            if len(raw_b64) < 1000 or "ERROR" in raw_b64:
                print("  [!] Bỏ qua - b64 quá ngắn hoặc dính lỗi 403 Token Error từ server")
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
