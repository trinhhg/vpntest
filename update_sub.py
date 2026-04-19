import requests
import base64
import urllib.parse
import re
import datetime
import yaml

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH  = f"{WORKER_DOMAIN}/api/push_data"

NODE_SUFFIX = "vpntrinhhg.pages.dev"

GROUP_RENAMES = [
    ('顶级机场', 'VPN Trinh Hg'),
    ('良心云',   'VPN Trinh Hg'),
    ('自动选择', 'Auto Select'),
    ('故障转移', 'Fallback'),
]

INFO_KEYWORDS = ['剩余流量', '距离下次重置', '套餐到期']

# Bảng dịch Trung → Anh (đã test với tên node thực tế)
CN_TO_EN = [
    # Cờ + tên nước (phải xử lý trước tên nước đơn)
    ("🇨🇳台湾","🇹🇼 Taiwan"), ("🇹🇼台湾","🇹🇼 Taiwan"),
    ("🇭🇰香港","🇭🇰 HK"), ("🇸🇬新加坡","🇸🇬 SG"),
    ("🇯🇵日本","🇯🇵 JP"), ("🇺🇸美国","🇺🇸 USA"),
    ("🇰🇷韩国","🇰🇷 KR"), ("🇩🇪德国","🇩🇪 DE"),
    ("🇬🇧英国","🇬🇧 UK"), ("🇧🇷巴西","🇧🇷 BR"),
    ("🇨🇦加拿大","🇨🇦 CA"), ("🇮🇳印度","🇮🇳 IN"),
    ("🇿🇦非洲","🇿🇦 ZA"), ("🇲🇽墨西哥","🇲🇽 MX"),
    ("🇸🇪瑞典","🇸🇪 SE"), ("🇦🇪迪拜","🇦🇪 Dubai"),
    # Tên nước đơn
    ("台湾","TW"), ("香港","HK"), ("新加坡","SG"),
    ("日本","JP"), ("美国","USA"), ("韩国","KR"),
    ("德国","DE"), ("英国","UK"), ("巴西","BR"),
    ("加拿大","CA"), ("印度","IN"), ("非洲","ZA"),
    ("墨西哥","MX"), ("瑞典","SE"), ("迪拜","Dubai"),
    # Thành phố
    ("洛杉矶","LA"), ("凤凰城","Phoenix"), ("法兰克福","Frankfurt"),
    ("伦敦","London"), ("圣保罗","Sao Paulo"), ("约翰内斯堡","JHB"),
    ("多伦多","Toronto"), ("斯德哥尔摩","Stockholm"), ("克雷塔罗","Queretaro"),
    ("孟买","Mumbai"), ("海得拉巴","Hyderabad"),
    # Tính năng (dài trước)
    ("三网高速","TriNet HS"), ("高速","HS"), ("专线","Direct"),
    ("流媒体","Stream"), ("三网","TriNet"),
    # Bội số (dài trước)
    ("1.5倍率","1.5x"), ("1.2倍率","1.2x"), ("1.8倍率","1.8x"),
    ("3.5倍率","3.5x"), ("2倍率","2x"), ("0.1倍","0.1x"), ("1倍","1x"),
    ("倍率","x"), ("倍","x"),
    # Số thứ tự (dài trước)
    ("1号","1"), ("2号","2"), ("3号","3"), ("4号","4"),
    ("5号","5"), ("6号","6"), ("7号","7"), ("号",""),
    # Ký tự đặc biệt → space
    ("—"," "), ("–"," "), ("|"," "),
    # Xóa tên nhà cung cấp
    ("顶级机场",""), ("良心云",""), ("自动选择",""), ("故障转移",""),
]


def is_info_node(name: str) -> bool:
    return any(k in name for k in INFO_KEYWORDS)


def clean_node_name(raw: str) -> str:
    """Dịch tên node Trung → Anh."""
    text = urllib.parse.unquote(raw)
    for cn, en in CN_TO_EN:
        text = text.replace(cn, en)
    text = re.sub(r'\bBGP\b', '', text, flags=re.IGNORECASE)
    # Xóa Hán còn sót
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf]+', '', text)
    # Chuẩn hóa spaces
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = text.strip(' -').strip()
    return text


def build_final_name(raw: str) -> str:
    c = clean_node_name(raw)
    return f"{c} - {NODE_SUFFIX}" if c else NODE_SUFFIX


# ──────────────────────────────────────────────────────────────────────────────
# XỬ LÝ BASE64
# ──────────────────────────────────────────────────────────────────────────────
def process_base64(content: str, rename_map: dict) -> str:
    padded = content + '=' * ((-len(content)) % 4)
    try:
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [!] b64 decode lỗi: {e}")
        return content

    new_lines = []
    for line in decoded.splitlines():
        line = line.strip()
        if not line:
            continue
        if "://" in line:
            parts = line.split("#", 1)
            if len(parts) == 2:
                old_name = urllib.parse.unquote(parts[1].strip())
                if is_info_node(old_name):
                    continue
                final_name = rename_map.get(old_name, build_final_name(old_name))
                new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    result_str = "\n".join(new_lines)
    return base64.b64encode(result_str.encode('utf-8')).decode('ascii')


# ──────────────────────────────────────────────────────────────────────────────
# XÓA INFO ENTRIES KHỎI INLINE LIST
# ──────────────────────────────────────────────────────────────────────────────
def remove_info_from_lists(text: str) -> str:
    for kw in INFO_KEYWORDS:
        # Có nháy đơn ở giữa: , 'kw...',
        text = re.sub(r",\s*'[^']*" + re.escape(kw) + r"[^']*'", '', text)
        # Có nháy kép ở giữa
        text = re.sub(r',\s*"[^"]*' + re.escape(kw) + r'[^"]*"', '', text)
        # Đầu list nháy đơn: ['kw...',
        text = re.sub(r"(?<=\[)'[^']*" + re.escape(kw) + r"[^']*',?\s*", '', text)
        # Đầu list nháy kép
        text = re.sub(r'(?<=\[)"[^"]*' + re.escape(kw) + r'[^"]*",?\s*', '', text)
        # Không nháy ở giữa/cuối: , kw..., hoặc , kw...]
        text = re.sub(r',\s*' + re.escape(kw) + r'[^,\[\]\'"{}]*(?=[,\]])', '', text)
        # Không nháy ở đầu: [kw...,
        text = re.sub(r'(?<=\[)' + re.escape(kw) + r'[^,\[\]\'"{}]*,?\s*', '', text)
    text = re.sub(r'\[\s*,\s*', '[', text)
    text = re.sub(r',\s*,+', ',', text)
    text = re.sub(r',\s*\]', ']', text)
    return text


# ──────────────────────────────────────────────────────────────────────────────
# ĐẢM BẢO TẤT CẢ TÊN TRONG PROXY-GROUPS LIST ĐỀU CÓ NHÁY ĐƠN
# ──────────────────────────────────────────────────────────────────────────────
def ensure_quoted_in_groups(yaml_text: str) -> str:
    """
    Quét proxy-groups section, đảm bảo mọi entry trong proxies: [...]
    đều được bọc trong nháy đơn. Điều này quan trọng cho Clash Go YAML parser.
    """
    in_proxy_groups = False
    lines = yaml_text.splitlines()
    result_lines = []

    for line in lines:
        stripped = line.strip()
        # Detect section
        if re.match(r'^proxy-groups\s*:', stripped):
            in_proxy_groups = True
        elif stripped and not line[0].isspace() and not stripped.startswith('-'):
            if not re.match(r'^proxy-groups\s*:', stripped):
                in_proxy_groups = False

        if in_proxy_groups and 'proxies:' in line and '[' in line:
            def quote_entries(m):
                content = m.group(1)
                entries = re.split(r',\s*', content)
                quoted = []
                for entry in entries:
                    entry = entry.strip()
                    if not entry:
                        continue
                    # Đã có nháy → giữ nguyên
                    if (entry.startswith("'") and entry.endswith("'")) or \
                       (entry.startswith('"') and entry.endswith('"')):
                        # Đổi nháy kép thành nháy đơn
                        if entry.startswith('"'):
                            entry = "'" + entry[1:-1] + "'"
                        quoted.append(entry)
                    else:
                        # Chưa có nháy → thêm nháy đơn
                        quoted.append(f"'{entry}'")
                return 'proxies: [' + ', '.join(quoted) + ']'

            line = re.sub(r'proxies:\s*\[([^\]]*)\]', quote_entries, line)

        result_lines.append(line)

    return '\n'.join(result_lines)


# ──────────────────────────────────────────────────────────────────────────────
# XỬ LÝ YAML HOÀN CHỈNH
# ──────────────────────────────────────────────────────────────────────────────
def process_yaml_raw(yaml_text: str, rename_map: dict) -> str:
    """
    Thứ tự xử lý:
    1. Xóa node rác trong proxies: section
    2. Xóa info entries khỏi proxy-groups proxies list
    3. Rename group names TRƯỚC (vì chúng xuất hiện trong list của group khác)
    4. Rename proxy names theo rename_map
    5. Đảm bảo tất cả entries trong proxy-groups list đều có nháy đơn
    """
    lines = yaml_text.splitlines()
    filtered = []
    i = 0
    in_proxies = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect section
        if re.match(r'^proxies\s*:', stripped):
            in_proxies = True
        elif re.match(r'^proxy-groups\s*:', stripped):
            in_proxies = False
        elif stripped and not line[0].isspace() and not stripped.startswith('-'):
            in_proxies = False

        # Xóa node rác trong proxies: section
        if in_proxies and re.match(r'^\s*-\s', line):
            nm = re.search(r"name:\s*['\"]?([^'\"{}]+?)['\"]?\s*[,}]", line)
            if nm and is_info_node(nm.group(1).strip()):
                i += 1
                while i < len(lines) and lines[i].startswith('    ') and not re.match(r'^\s*-\s', lines[i]):
                    i += 1
                continue

        filtered.append(line)
        i += 1

    result = '\n'.join(filtered)

    # Bước 2: Xóa info entries khỏi proxy-groups lists
    result = remove_info_from_lists(result)

    # Bước 3: Rename group names TRƯỚC (toàn bộ văn bản)
    for old_g, new_g in GROUP_RENAMES:
        result = result.replace(old_g, new_g)

    # Bước 4: Rename proxy nodes
    sorted_items = sorted(rename_map.items(), key=lambda x: len(x[0]), reverse=True)
    for old_name, new_name in sorted_items:
        if not old_name or old_name == new_name:
            continue
        # name: 'old' / name: "old"
        result = result.replace(f"name: '{old_name}'", f"name: '{new_name}'")
        result = result.replace(f'name: "{old_name}"', f'name: "{new_name}"')
        # name: old, (inline block)
        result = re.sub(r'(name:\s)' + re.escape(old_name) + r'(\s*[,}])',
                        r'\g<1>' + new_name + r'\g<2>', result)
        # Trong list: 'old' / "old"
        result = result.replace(f"'{old_name}'", f"'{new_name}'")
        result = result.replace(f'"{old_name}"', f'"{new_name}"')
        # Trong list không nháy
        result = result.replace(f", {old_name},", f", {new_name},")
        result = result.replace(f"[{old_name},", f"[{new_name},")
        result = result.replace(f", {old_name}]", f", {new_name}]")
        result = result.replace(f"[{old_name}]", f"[{new_name}]")

    # Bước 5: Đảm bảo tất cả entries trong proxy-groups list đều có nháy đơn
    # → Tránh Clash Go YAML parser đọc sai tên chứa dấu '-'
    result = ensure_quoted_in_groups(result)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# BUILD RENAME MAP
# ──────────────────────────────────────────────────────────────────────────────
def build_rename_map(decoded_b64: str, yaml_text: str) -> dict:
    rename_map = {}

    for line in decoded_b64.splitlines():
        line = line.strip()
        if "://" in line and "#" in line:
            parts = line.split("#", 1)
            old = urllib.parse.unquote(parts[1].strip())
            if old and not is_info_node(old):
                rename_map[old] = build_final_name(old)

    try:
        y = yaml.safe_load(yaml_text)
        if y and isinstance(y, dict):
            for p in (y.get('proxies') or []):
                n = p.get('name', '')
                if n and not is_info_node(n) and n not in rename_map:
                    rename_map[n] = build_final_name(n)
    except Exception as e:
        print(f"  [!] YAML safe_load lỗi: {e}")

    return rename_map


# ──────────────────────────────────────────────────────────────────────────────
# HÀM CHÍNH
# ──────────────────────────────────────────────────────────────────────────────
def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=15)
        res.raise_for_status()
        links_db = res.json()
        print(f"Tổng link DB: {len(links_db)}")
    except Exception as e:
        print(f"[!] Không lấy được links DB: {e}")
        return

    # Chỉ fetch token GỐC
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
            b64_res  = requests.get(orig_url, headers={"User-Agent": "v2rayN/6.23"}, timeout=20)
            yaml_res = requests.get(orig_url, headers={"User-Agent": "ClashForWindows/0.20.39"}, timeout=20)

            if b64_res.status_code != 200:
                print(f"  [!] Base64 HTTP {b64_res.status_code}")
                continue

            print(f"  b64  CT: {b64_res.headers.get('Content-Type','?')[:50]}")
            print(f"  yaml CT: {yaml_res.headers.get('Content-Type','?')[:50]}")
            print(f"  yaml[0]: {yaml_res.text.split(chr(10))[0].strip()[:80]}")

            b64_raw   = b64_res.text.strip()
            yaml_raw  = yaml_res.text.strip()
            user_info = b64_res.headers.get("subscription-userinfo", "")

            # Traffic
            traffic = {"used":"0.00","total":"0.00","percent":0,"expire":"Vĩnh viễn"}
            if user_info:
                def gi(p): m=re.search(p, user_info); return int(m.group(1)) if m else 0
                up=gi(r'upload=(\d+)'); dn=gi(r'download=(\d+)')
                tot=gi(r'total=(\d+)'); exp=gi(r'expire=(\d+)')
                used_gb=(up+dn)/1_073_741_824; total_gb=tot/1_073_741_824
                pct=round((used_gb/total_gb)*100) if total_gb>0 else 0
                exp_str=datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp>0 else "Vĩnh viễn"
                traffic={"used":f"{used_gb:.2f}","total":f"{total_gb:.2f}","percent":pct,"expire":exp_str}

            # Decode b64 để build rename_map
            padded = b64_raw + '=' * ((-len(b64_raw)) % 4)
            try:
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  [!] Decode lỗi: {e}"); decoded = ""

            rename_map = build_rename_map(decoded, yaml_raw)
            print(f"  rename_map: {len(rename_map)} entries")

            # Xử lý base64
            final_b64 = process_base64(b64_raw, rename_map)
            try:
                base64.b64decode(final_b64 + '=' * ((-len(final_b64)) % 4))
                print(f"  [OK] b64 verified ({len(final_b64)} chars)")
            except Exception as e:
                print(f"  [WARN] b64 verify failed: {e} → dùng raw")
                final_b64 = b64_raw

            # Xử lý YAML
            final_yaml = ""
            first_line = yaml_raw.split('\n')[0].strip() if yaml_raw else ""
            yaml_valid = any(first_line.startswith(k) for k in
                             ['proxies','mixed-port','port:','allow-lan','mode:','log-level'])

            if yaml_valid:
                final_yaml = process_yaml_raw(yaml_raw, rename_map)
                # Verify YAML có thể parse được
                try:
                    y_check = yaml.safe_load(final_yaml)
                    group_names = {g['name'] for g in y_check.get('proxy-groups',[])}
                    proxy_names = {p['name'] for p in y_check.get('proxies',[])}
                    all_names = proxy_names | group_names
                    errors = []
                    for g in y_check.get('proxy-groups',[]):
                        for p in g.get('proxies',[]):
                            if p not in all_names:
                                errors.append(f"'{p}' in '{g['name']}'")
                    if errors:
                        print(f"  [WARN] Group proxy not found: {errors[:3]}")
                    else:
                        print(f"  [OK] YAML verify: {len(proxy_names)} proxies, {len(group_names)} groups ✅")
                except Exception as e:
                    print(f"  [WARN] YAML verify lỗi: {e}")

                cn_left = list(set(re.findall(r'[\u4e00-\u9fff]+', final_yaml)))
                if cn_left:
                    print(f"  [WARN] Còn Hán: {cn_left[:5]}")
                print(f"  [OK] YAML: {len(final_yaml)} chars")
            else:
                print(f"  [!] Không phải YAML Clash. First: '{first_line[:60]}'")

            payload = {
                "key": token, "body_b64": final_b64,
                "body_yaml": final_yaml, "info": user_info, "traffic": traffic
            }
            push_res = requests.post(API_PUSH, json=payload, timeout=15)
            print(f"  [OK] Push → HTTP {push_res.status_code}")

        except Exception as e:
            print(f"  [!] Lỗi: {e}")
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    update_all_subs()
