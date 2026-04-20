"""
update_sub.py — VPN Trinh Hg subscription updater

Fix lần này:
- Node thông tin có tiếng Việt đầy đủ dấu (encode UTF-8 đúng)
- 4 info nodes (thêm Zalo)
- Tên sub = "VPN Trinh Hg" (không phải VPN_Trinh_Hg.yaml)
- Thêm UA fetch cho Mihomo/Clash Meta
- YAML verify sau khi xử lý
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

# ─── 4 Node thông tin tự build (đặt ở đầu) ──────────────────────────────────
INFO_NODES_NEW = [
    "🇻🇳 Truy cập web bên dưới",
    "🇻🇳 Để xem thêm gói khác",
    "🌐 Website: vpntrinhhg.pages.dev",
    "📞 Zalo: 0917678211",
]

# ─── Keyword info nodes từ link gốc (sẽ bị xóa) ─────────────────────────────
INFO_KEYWORDS = ['剩余流量', '距离下次重置', '套餐到期']

# ─── Rename group ─────────────────────────────────────────────────────────────
GROUP_RENAMES = {
    '顶级机场': 'VPN Trinh Hg',
    '良心云':   'VPN Trinh Hg',
    '自动选择': 'Auto Select',
    '故障转移': 'Fallback',
}

# ─── Bảng rename cố định ──────────────────────────────────────────────────────
FIXED_RENAME = {
    # ── DJJC ──
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
    # ── Liangxin ──
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


def get_new_name(old: str) -> str:
    return FIXED_RENAME.get(old, old)


# ─────────────────────────────────────────────────────────────────────────────
# BASE64
# ─────────────────────────────────────────────────────────────────────────────
def process_base64(content: str) -> str:
    padded = content + '=' * ((-len(content)) % 4)
    try:
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [!] b64 decode lỗi: {e}")
        return content

    # 4 info nodes UTF-8 đúng (có dấu tiếng Việt)
    new_lines = []
    for info_name in INFO_NODES_NEW:
        # Encode đúng UTF-8 để # fragment không bị vỡ
        new_lines.append(
            f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:1?type=tcp"
            f"#{urllib.parse.quote(info_name, safe='')}"
        )

    for line in decoded.splitlines():
        line = line.strip()
        if not line:
            continue
        if "://" in line:
            if "#" in line:
                idx = line.index("#")
                proto = line[:idx]
                old_name = urllib.parse.unquote(line[idx+1:].strip())
                if is_info_node(old_name):
                    continue
                new_name = get_new_name(old_name)
                new_lines.append(f"{proto}#{urllib.parse.quote(new_name, safe='')}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    result_str = "\n".join(new_lines)
    return base64.b64encode(result_str.encode('utf-8')).decode('ascii')


# ─────────────────────────────────────────────────────────────────────────────
# YAML DUMP helpers
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
    if isinstance(v, bool):
        return str(v).lower()
    if not isinstance(v, str):
        return str(v)
    if _needs_quote(v):
        return "'" + v.replace("'", "''") + "'"
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


def dump_yaml_clash(y_obj: dict, original_yaml: str) -> str:
    """Giữ header gốc, rebuild proxies/proxy-groups/rules."""
    # Tách header: mọi thứ trước 'proxies:'
    header_match = re.split(r'^proxies\s*:', original_yaml, maxsplit=1, flags=re.MULTILINE)
    header = header_match[0].rstrip() if len(header_match) > 1 else ""

    lines = [header, "proxies:"]
    for p in y_obj.get('proxies', []):
        lines.append(_proxy_to_inline(p))
    lines.append("proxy-groups:")
    for g in y_obj.get('proxy-groups', []):
        lines.append(_group_to_inline(g))
    lines.append("rules:")
    for r in y_obj.get('rules', []):
        lines.append(f"    - {_q(r)}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# YAML PROCESS
# ─────────────────────────────────────────────────────────────────────────────
def process_yaml(yaml_text: str) -> str:
    try:
        y = yaml.safe_load(yaml_text)
    except Exception as e:
        print(f"  [!] YAML parse lỗi: {e}")
        return yaml_text
    if not y or not isinstance(y, dict):
        return yaml_text

    removed_names = {p['name'] for p in (y.get('proxies') or [])
                     if is_info_node(p.get('name', ''))}

    # ── Proxies mới ──
    new_proxies = []
    for info in INFO_NODES_NEW:
        new_proxies.append({
            'name': info, 'type': 'vless',
            'server': '127.0.0.1', 'port': 1,
            'uuid': '00000000-0000-0000-0000-000000000000', 'udp': False,
        })
    for p in (y.get('proxies') or []):
        n = p.get('name', '')
        if n in removed_names:
            continue
        p = dict(p)
        p['name'] = get_new_name(n)
        new_proxies.append(p)

    # Map tên cũ → mới
    name_map = {p.get('name',''): get_new_name(p.get('name',''))
                for p in (y.get('proxies') or []) if p.get('name','') not in removed_names}

    # ── Groups mới ──
    new_groups = []
    for g in (y.get('proxy-groups') or []):
        new_g = dict(g)
        new_g['name'] = GROUP_RENAMES.get(g['name'], g['name'])
        is_main = (new_g['name'] == 'VPN Trinh Hg')
        new_list = []
        if is_main:
            new_list.extend(INFO_NODES_NEW)
        for p_ref in g.get('proxies', []):
            if is_info_node(p_ref):
                continue
            r = GROUP_RENAMES.get(p_ref, p_ref)
            r = name_map.get(r, r)
            if is_main and r in INFO_NODES_NEW:
                continue
            new_list.append(r)
        new_g['proxies'] = new_list
        new_groups.append(new_g)

    # ── Rules mới ──
    new_rules = []
    for r in (y.get('rules') or []):
        for og, ng in GROUP_RENAMES.items():
            r = r.replace(og, ng)
        new_rules.append(r)

    y['proxies']      = new_proxies
    y['proxy-groups'] = new_groups
    y['rules']        = new_rules

    result = dump_yaml_clash(y, yaml_text)

    # Verify
    try:
        y2 = yaml.safe_load(result)
        pnames = {p['name'] for p in y2.get('proxies', [])}
        gnames = {g['name'] for g in y2.get('proxy-groups', [])}
        all_n  = pnames | gnames
        errors = [f"'{p}' in '{g['name']}'"
                  for g in y2.get('proxy-groups', [])
                  for p in g.get('proxies', [])
                  if p not in all_n]
        if errors:
            print(f"  [WARN] Proxy not found: {errors[:3]}")
        else:
            print(f"  [OK] YAML ✅ ({len(pnames)} proxies, {len(gnames)} groups)")
    except Exception as e:
        print(f"  [WARN] YAML re-parse lỗi: {e}")

    return result


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
        print(f"\n→ Token: {token[:10]}...")
        try:
            # Fetch b64
            b64_res = requests.get(orig_url,
                headers={"User-Agent": "v2rayN/6.23"}, timeout=20)
            # Fetch YAML – thử ClashMeta trước, fallback sang ClashForWindows
            yaml_res = requests.get(orig_url,
                headers={"User-Agent": "Mihomo/1.18.6"}, timeout=20)
            if not yaml_res.text.strip().startswith(('proxies','mixed-port','port:','allow-lan','mode:','log-level')):
                yaml_res = requests.get(orig_url,
                    headers={"User-Agent": "ClashForWindows/0.20.39"}, timeout=20)

            if b64_res.status_code != 200:
                print(f"  [!] Base64 HTTP {b64_res.status_code}")
                continue

            b64_raw   = b64_res.text.strip()
            yaml_raw  = yaml_res.text.strip()
            user_info = b64_res.headers.get("subscription-userinfo", "")

            print(f"  yaml first: {yaml_raw[:60]}")

            # Traffic
            traffic = {"used":"0.00","total":"0.00","percent":0,"expire":"Vĩnh viễn"}
            if user_info:
                def gi(p): m=re.search(p, user_info); return int(m.group(1)) if m else 0
                up=gi(r'upload=(\d+)'); dn=gi(r'download=(\d+)')
                tot=gi(r'total=(\d+)'); exp=gi(r'expire=(\d+)')
                used_gb=(up+dn)/1_073_741_824; total_gb=tot/1_073_741_824
                pct=round((used_gb/total_gb)*100) if total_gb>0 else 0
                exp_str=(datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y')
                         if exp>0 else "Vĩnh viễn")
                traffic={"used":f"{used_gb:.2f}","total":f"{total_gb:.2f}",
                         "percent":pct,"expire":exp_str}

            # Process b64
            final_b64 = process_base64(b64_raw)
            try:
                base64.b64decode(final_b64 + '='*((-len(final_b64))%4))
                print(f"  [OK] b64 ({len(final_b64)} chars)")
            except Exception as e:
                print(f"  [WARN] b64 verify: {e}")
                final_b64 = b64_raw

            # Process YAML
            final_yaml = ""
            yaml_valid = any(yaml_raw.startswith(k) for k in
                             ['proxies','mixed-port','port:','allow-lan','mode:','log-level'])
            if yaml_valid:
                final_yaml = process_yaml(yaml_raw)
                print(f"  [OK] YAML ({len(final_yaml)} chars)")
            else:
                print(f"  [!] Không phải YAML Clash: '{yaml_raw[:50]}'")

            payload = {"key":token,"body_b64":final_b64,
                       "body_yaml":final_yaml,"info":user_info,"traffic":traffic}
            push_res = requests.post(API_PUSH, json=payload, timeout=15)
            print(f"  [OK] Push → {push_res.status_code}")

        except Exception as e:
            print(f"  [!] Lỗi: {e}")
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    update_all_subs()
