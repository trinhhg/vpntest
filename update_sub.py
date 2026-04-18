import requests
import base64
import urllib.parse
import re
import datetime
import yaml

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH  = f"{WORKER_DOMAIN}/api/push_data"

# Suffix gắn cuối mỗi tên node
NODE_SUFFIX = "vpntrinhhg.pages.dev"

# ──────────────────────────────────────────────────────────────────────────────
# BẢNG RENAME GROUP CỐ ĐỊNH
# QUAN TRỌNG: Thứ tự dài trước để tránh replace nhầm chuỗi con
# ──────────────────────────────────────────────────────────────────────────────
GROUP_RENAMES = [
    ('顶级机场', 'VPN Trinh Hg'),
    ('良心云',   'VPN Trinh Hg'),
    ('自动选择', 'Auto Select'),
    ('故障转移', 'Fallback'),
]

# Từ khóa node rác (thông tin tài khoản, không phải node thật)
INFO_KEYWORDS = ['剩余流量', '距离下次重置', '套餐到期']

# Tất cả cặp tiếng Trung → tiếng Anh (sắp xếp dài trước)
CN_TO_EN = [
    # Quốc gia / vùng lãnh thổ
    ("🇨🇳台湾",   "🇹🇼 Taiwan"),
    ("🇹🇼台湾",   "🇹🇼 Taiwan"),
    ("台湾",       "Taiwan"),
    ("🇭🇰香港",   "🇭🇰 HongKong"),
    ("香港",       "HongKong"),
    ("🇸🇬新加坡", "🇸🇬 Singapore"),
    ("新加坡",     "Singapore"),
    ("🇯🇵日本",   "🇯🇵 Japan"),
    ("日本",       "Japan"),
    ("🇺🇸美国",   "🇺🇸 USA"),
    ("美国",       "USA"),
    ("🇰🇷韩国",   "🇰🇷 Korea"),
    ("韩国",       "Korea"),
    ("🇩🇪德国",   "🇩🇪 Germany"),
    ("德国",       "Germany"),
    ("🇬🇧英国",   "🇬🇧 UK"),
    ("英国",       "UK"),
    ("🇫🇷法国",   "🇫🇷 France"),
    ("法国",       "France"),
    ("🇧🇷巴西",   "🇧🇷 Brazil"),
    ("巴西",       "Brazil"),
    ("🇦🇺澳大利亚","🇦🇺 Australia"),
    ("澳大利亚",   "Australia"),
    ("🇨🇦加拿大", "🇨🇦 Canada"),
    ("加拿大",     "Canada"),
    ("🇮🇳印度",   "🇮🇳 India"),
    ("印度",       "India"),
    ("🇿🇦非洲",   "🇿🇦 Africa"),
    ("非洲",       "Africa"),
    ("🇲🇽墨西哥", "🇲🇽 Mexico"),
    ("墨西哥",     "Mexico"),
    ("🇸🇪瑞典",   "🇸🇪 Sweden"),
    ("瑞典",       "Sweden"),
    ("🇦🇪迪拜",   "🇦🇪 Dubai"),
    ("迪拜",       "Dubai"),
    # Thành phố phổ biến
    ("洛杉矶",     "LA"),
    ("凤凰城",     "Phoenix"),
    ("法兰克福",   "Frankfurt"),
    ("伦敦",       "London"),
    ("圣保罗",     "SaoPaulo"),
    ("约翰内斯堡", "Johannesburg"),
    ("多伦多",     "Toronto"),
    ("斯德哥尔摩", "Stockholm"),
    ("克雷塔罗",   "Queretaro"),
    ("孟买",       "Mumbai"),
    ("海得拉巴",   "Hyderabad"),
    # Tính năng / chất lượng
    ("三网高速",   "TriNet-HighSpeed"),
    ("高速",       "HighSpeed"),
    ("专线",       "Private"),
    ("流媒体",     "Streaming"),
    ("三网",       "TriNet"),
    ("0.1倍",      "0.1x"),
    ("0.1",        "0.1x"),
    # Ký tự phân cách hay gặp
    ("—",          "-"),
    ("–",          "-"),
    # Tên nhà cung cấp (xóa)
    ("顶级机场",   ""),
    ("良心云",     ""),
    ("自动选择",   ""),
    ("故障转移",   ""),
    # Số + từ tiếng Trung phổ biến
    ("号",         ""),
    ("倍率",       "x"),
    ("倍",         "x"),
]


def is_info_node(name: str) -> bool:
    return any(k in name for k in INFO_KEYWORDS)


def clean_node_name(raw: str) -> str:
    """Dịch tên node Trung → Anh, trả về tên sạch."""
    text = urllib.parse.unquote(raw)

    for cn, en in CN_TO_EN:
        text = text.replace(cn, en)

    # Xóa BGP, xóa ký tự thừa
    text = re.sub(r'(?i)\bbgp\b', '', text)
    # Chuẩn hóa dấu gạch ngang
    text = re.sub(r'[-\s]+', ' ', text).strip()
    text = re.sub(r'\s*-\s*', ' - ', text)
    # Xóa dấu - đầu/cuối
    text = text.strip(' -').strip()

    # Xóa các ký tự tiếng Trung còn sót (nếu có)
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip().strip(' -').strip()

    return text


def build_final_name(raw: str) -> str:
    clean = clean_node_name(raw)
    return f"{clean} - {NODE_SUFFIX}" if clean else NODE_SUFFIX


# ──────────────────────────────────────────────────────────────────────────────
# XỬ LÝ BASE64
# ──────────────────────────────────────────────────────────────────────────────
def process_base64(content: str, rename_map: dict) -> str:
    # Pad
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
    encoded = base64.b64encode(result_str.encode('utf-8')).decode('ascii')
    return encoded


# ──────────────────────────────────────────────────────────────────────────────
# XỬ LÝ YAML — string replace trực tiếp, KHÔNG dùng yaml.dump
# ──────────────────────────────────────────────────────────────────────────────
def process_yaml_raw(yaml_text: str, rename_map: dict) -> str:
    """
    Thứ tự xử lý:
    1. Xóa dòng node rác
    2. Rename group cố định TRƯỚC (vì chúng xuất hiện trong proxies list của group)
    3. Rename proxy node theo rename_map
    """

    # ── Bước 1: Xóa node rác ──
    lines = yaml_text.splitlines()
    filtered = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Inline: "  - { name: 'xxx', ... }"
        if re.match(r'^\s*-\s*\{', line):
            if any(k in line for k in INFO_KEYWORDS):
                i += 1
                continue
            filtered.append(line)
            i += 1
            continue

        # Block: "  - name: xxx"
        if re.match(r'^\s*-\s+name:', line):
            nm = re.search(r"name:\s*['\"]?(.+?)['\"]?\s*$", line)
            if nm:
                raw = nm.group(1).strip().strip("'\"")
                if is_info_node(raw):
                    i += 1
                    # Skip các dòng thuộc tính của proxy này
                    while i < len(lines):
                        if lines[i].startswith('    ') and not re.match(r'^\s*-\s', lines[i]):
                            i += 1
                        else:
                            break
                    continue
            filtered.append(line)
            i += 1
            continue

        filtered.append(line)
        i += 1

    result = '\n'.join(filtered)

    # ── Bước 2: Rename group cố định TRƯỚC ──
    # Dùng word-boundary để tránh replace nhầm bên trong tên proxy node
    # Nhưng vì tên group xuất hiện trong proxies: list nên cần replace toàn bộ
    for old_g, new_g in GROUP_RENAMES:
        # Trong name: field
        result = result.replace(f"name: '{old_g}'", f"name: '{new_g}'")
        result = result.replace(f'name: "{old_g}"', f'name: "{new_g}"')
        result = result.replace(f"name: {old_g}\n", f"name: {new_g}\n")
        # Trong proxies list của group: '- old' hoặc "- old"
        result = result.replace(f"      - '{old_g}'", f"      - '{new_g}'")
        result = result.replace(f"    - '{old_g}'",   f"    - '{new_g}'")
        result = result.replace(f'      - "{old_g}"', f'      - "{new_g}"')
        result = result.replace(f'    - "{old_g}"',   f'    - "{new_g}"')
        # Trong inline list [..., 'old', ...]
        result = result.replace(f"'{old_g}'", f"'{new_g}'")
        result = result.replace(f'"{old_g}"', f'"{new_g}"')
        # Không có nháy trong list: [a, b, old, c] hoặc ,old]
        result = re.sub(
            r'(?<=[,\[]\s{0,4})' + re.escape(old_g) + r'(?=\s*[,\]])',
            new_g, result
        )
        # Trong rules target: ",old'" hoặc ",old\n"
        result = re.sub(
            r'(,\s*)' + re.escape(old_g) + r"(']?$)",
            r'\g<1>' + new_g + r'\g<2>',
            result, flags=re.MULTILINE
        )

    # ── Bước 3: Rename proxy node theo rename_map ──
    sorted_items = sorted(rename_map.items(), key=lambda x: len(x[0]), reverse=True)

    for old_name, new_name in sorted_items:
        if not old_name or old_name == new_name:
            continue
        # name: 'old' / name: "old"
        result = result.replace(f"name: '{old_name}'", f"name: '{new_name}'")
        result = result.replace(f'name: "{old_name}"', f'name: "{new_name}"')
        # name: old (cuối dòng)
        result = re.sub(
            r'(name:\s+)' + re.escape(old_name) + r'(\s*)$',
            r'\g<1>' + new_name + r'\g<2>',
            result, flags=re.MULTILINE
        )
        # Trong list: '- 'old'' các mức thụt lề khác nhau
        for indent in ['      ', '    ', '  ']:
            result = result.replace(f"{indent}- '{old_name}'", f"{indent}- '{new_name}'")
            result = result.replace(f'{indent}- "{old_name}"', f'{indent}- "{new_name}"')
        # Inline: 'old' hoặc "old"
        result = result.replace(f"'{old_name}'", f"'{new_name}'")
        result = result.replace(f'"{old_name}"', f'"{new_name}"')
        # Inline list không có nháy
        result = re.sub(
            r'(?<=[,\[]\s{0,4})' + re.escape(old_name) + r'(?=\s*[,\]])',
            new_name, result
        )

    return result


# ──────────────────────────────────────────────────────────────────────────────
# BUILD RENAME MAP từ base64 decoded + YAML
# ──────────────────────────────────────────────────────────────────────────────
def build_rename_map(decoded_b64: str, yaml_text: str) -> dict:
    rename_map = {}

    for line in decoded_b64.splitlines():
        line = line.strip()
        if "://" in line and "#" in line:
            parts = line.split("#", 1)
            old = urllib.parse.unquote(parts[1].strip())
            if not is_info_node(old) and old:
                rename_map[old] = build_final_name(old)

    try:
        y = yaml.safe_load(yaml_text)
        if y and isinstance(y, dict):
            for p in (y.get('proxies') or []):
                n = p.get('name', '')
                if n and not is_info_node(n) and n not in rename_map:
                    rename_map[n] = build_final_name(n)
    except Exception as e:
        print(f"  [!] YAML parse để build rename_map lỗi: {e}")

    return rename_map


# ──────────────────────────────────────────────────────────────────────────────
# HÀM CHÍNH
# ──────────────────────────────────────────────────────────────────────────────
def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=15)
        res.raise_for_status()
        links_db = res.json()
        print(f"Tổng link trong DB: {len(links_db)}")
    except Exception as e:
        print(f"[!] Không lấy được links DB: {e}")
        return

    # Chỉ fetch link GỐC (không fetch link ẩn)
    unique_origins = {}
    for item in links_db:
        orig_url = item.get("orig")
        if not orig_url:
            continue
        try:
            parsed = urllib.parse.urlparse(orig_url)
            qs = urllib.parse.parse_qs(parsed.query)
            token_list = qs.get("OwO") or qs.get("token")
            if token_list:
                unique_origins[token_list[0]] = orig_url
        except Exception:
            continue

    print(f"Link gốc cần fetch: {len(unique_origins)}")

    for token, orig_url in unique_origins.items():
        print(f"\n→ Token: {token[:10]}...")
        try:
            # Fetch dạng base64
            b64_res = requests.get(
                orig_url,
                headers={"User-Agent": "v2rayN/6.23"},
                timeout=20
            )
            # Fetch dạng YAML Clash
            yaml_res = requests.get(
                orig_url,
                headers={"User-Agent": "ClashForWindows/0.20.39"},
                timeout=20
            )

            if b64_res.status_code != 200:
                print(f"  [!] Base64 HTTP {b64_res.status_code}")
                continue

            print(f"  b64  status : {b64_res.status_code} | CT: {b64_res.headers.get('Content-Type','?')[:40]}")
            print(f"  yaml status : {yaml_res.status_code} | CT: {yaml_res.headers.get('Content-Type','?')[:40]}")
            print(f"  yaml preview: {yaml_res.text[:120].strip()}")

            b64_raw      = b64_res.text.strip()
            yaml_raw     = yaml_res.text.strip()
            user_info    = b64_res.headers.get("subscription-userinfo", "")

            # ── Traffic ──
            traffic = {"used": "0.00", "total": "0.00", "percent": 0, "expire": "Vĩnh viễn"}
            if user_info:
                def gi(pattern):
                    m = re.search(pattern, user_info)
                    return int(m.group(1)) if m else 0
                up  = gi(r'upload=(\d+)')
                dn  = gi(r'download=(\d+)')
                tot = gi(r'total=(\d+)')
                exp = gi(r'expire=(\d+)')
                used_gb  = (up + dn) / 1_073_741_824
                total_gb = tot / 1_073_741_824
                pct      = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                exp_str  = datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp > 0 else "Vĩnh viễn"
                traffic  = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": pct, "expire": exp_str}

            # ── Decode base64 để build rename_map ──
            padded = b64_raw + '=' * ((-len(b64_raw)) % 4)
            try:
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  [!] Decode lỗi: {e}")
                decoded = ""

            rename_map = build_rename_map(decoded, yaml_raw)
            print(f"  rename_map: {len(rename_map)} entries")

            # ── Xử lý base64 ──
            final_b64 = process_base64(b64_raw, rename_map)
            # Xác minh decode lại được
            try:
                test_pad = final_b64 + '=' * ((-len(final_b64)) % 4)
                base64.b64decode(test_pad)
                print(f"  [OK] base64 verify passed ({len(final_b64)} chars)")
            except Exception as e:
                print(f"  [WARN] base64 verify failed: {e} — dùng raw")
                final_b64 = b64_raw

            # ── Xử lý YAML ──
            final_yaml = ""
            first_line = yaml_raw.split('\n')[0].strip() if yaml_raw else ""
            yaml_valid = any(first_line.startswith(k) for k in
                             ['proxies', 'mixed-port', 'port:', 'allow-lan', 'mode:', 'log-level'])

            if yaml_valid:
                final_yaml = process_yaml_raw(yaml_raw, rename_map)
                print(f"  [OK] YAML processed: {len(final_yaml)} chars")
                # Cảnh báo nếu còn chữ Hán
                cn_left = list(set(re.findall(r'[\u4e00-\u9fff]+', final_yaml)))
                if cn_left:
                    # Bỏ qua các false positive (ký tự trong comment, URL)
                    real_cn = [c for c in cn_left if len(c) > 1]
                    if real_cn:
                        print(f"  [WARN] Còn chữ Hán: {real_cn[:8]}")
            else:
                print(f"  [!] Không phải YAML Clash (first_line='{first_line[:40]}')")
                print(f"      → Thử UA khác nếu cần: 'clash-verge' hoặc 'Stash'")

            # ── Push lên KV ──
            payload = {
                "key":       token,
                "body_b64":  final_b64,
                "body_yaml": final_yaml,
                "info":      user_info,
                "traffic":   traffic
            }
            push_res = requests.post(API_PUSH, json=payload, timeout=15)
            print(f"  [OK] Push → HTTP {push_res.status_code}")

        except Exception as e:
            print(f"  [!] Lỗi xử lý token {token[:10]}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    update_all_subs()
