import requests
import base64
import urllib.parse
import re
import datetime
import yaml

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH  = f"{WORKER_DOMAIN}/api/push_data"

GROUP_RENAMES = [
    ('顶级机场', 'VPN Trinh Hg'),
    ('良心云',   'VPN Trinh Hg'),
    ('自动选择', 'Auto Select'),
    ('故障转移', 'Fallback'),
]

INFO_KEYWORDS = ['剩余流量', '距离下次重置', '套餐到期']


def is_info_node(name: str) -> bool:
    return any(k in name for k in INFO_KEYWORDS)


def clean_text_global(text: str) -> str:
    text = urllib.parse.unquote(text)
    replacements = [
        ("🇨🇳台湾", "🇹🇼 Taiwan "), ("台湾", "Taiwan "),
        ("🇭🇰香港", "🇭🇰 Hong Kong "), ("香港", "Hong Kong "),
        ("🇸🇬新加坡", "🇸🇬 Singapore "), ("新加坡", "Singapore "),
        ("🇯🇵日本", "🇯🇵 Japan "), ("日本", "Japan "),
        ("🇺🇸美国", "🇺🇸 USA "), ("美国", "USA "),
        ("🇰🇷韩国", "🇰🇷 Korea "), ("韩国", "Korea "),
        ("高速", " High Speed "), ("专线", " Private "),
        ("流媒体", " Streaming"), ("0.1倍", " 0.1x"),
        ("三网", " TriNet "), ("顶级机场", ""), ("良心云", ""),
        ("自动选择", ""), ("故障转移", ""),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r'(?i)bgp', '', text)
    text = re.sub(r'[|\-]+', '-', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(" -", "-").replace("- ", "-").replace("-", " - ")
    if text.endswith("-"):
        text = text[:-1].strip()
    return text


def build_final_name(raw_name: str) -> str:
    clean = clean_text_global(raw_name)
    if clean.startswith("-"):
        clean = clean[1:].strip()
    return f"{clean} - VPN Trinh Hg" if clean else "VPN Trinh Hg"


def process_base64(content: str, rename_map: dict) -> str:
    missing = len(content) % 4
    if missing:
        content += '=' * (4 - missing)
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [!] base64 decode lỗi: {e}")
        return content

    new_lines = []
    for line in decoded.splitlines():
        line = line.strip()
        if not line:
            continue
        if "://" in line:
            parts = line.split("#", 1)
            if len(parts) == 2:
                old_name = urllib.parse.unquote(parts[1])
                if is_info_node(old_name):
                    continue
                final_name = rename_map.get(old_name, build_final_name(old_name))
                new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    return base64.b64encode("\n".join(new_lines).encode()).decode()


def process_yaml_raw(yaml_text: str, rename_map: dict) -> str:
    """
    Xử lý YAML trực tiếp trên chuỗi thô — KHÔNG dùng yaml.dump.
    Bước 1: Xóa dòng proxy rác (node thông tin)
    Bước 2: Rename tên proxy theo rename_map
    Bước 3: Rename tên group cố định
    
    QUAN TRỌNG: Bước 3 phải chạy SAU bước 2 để đảm bảo
    tên group trong proxy-groups.proxies list cũng được cập nhật
    trước khi rename group name chính.
    """
    # ---- Bước 1: Lọc node rác ----
    lines = yaml_text.splitlines()
    filtered = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Inline proxy: "  - { name: 'xxx', ... }"
        if re.match(r'^\s*-\s*\{', line):
            if any(k in line for k in INFO_KEYWORDS):
                i += 1
                continue
            filtered.append(line)
            i += 1
            continue

        # Block proxy: "  - name: xxx"
        if re.match(r'^\s*-\s+name:', line):
            nm = re.search(r"name:\s*['\"]?(.+?)['\"]?\s*$", line)
            if nm and is_info_node(nm.group(1).strip().strip("'\"")):
                i += 1
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

    # ---- Bước 2: Rename proxy name theo rename_map ----
    # Sắp xếp theo độ dài giảm dần để tránh replace nhầm
    sorted_items = sorted(rename_map.items(), key=lambda x: len(x[0]), reverse=True)

    for old_name, new_name in sorted_items:
        if not old_name or old_name == new_name:
            continue

        # Dạng: name: 'old' hoặc name: "old"
        result = result.replace(f"name: '{old_name}'", f"name: '{new_name}'")
        result = result.replace(f'name: "{old_name}"', f'name: "{new_name}"')

        # Dạng: name: old (cuối dòng, không có nháy)
        result = re.sub(
            r'(name:\s+)' + re.escape(old_name) + r'(\s*)$',
            r'\g<1>' + new_name + r'\g<2>',
            result, flags=re.MULTILINE
        )

        # Dạng trong list: '- ''old''' hoặc '- "old"'
        result = result.replace(f"      - '{old_name}'", f"      - '{new_name}'")
        result = result.replace(f'      - "{old_name}"', f'      - "{new_name}"')
        result = result.replace(f"    - '{old_name}'", f"    - '{new_name}'")
        result = result.replace(f'    - "{old_name}"', f'    - "{new_name}"')

        # Dạng inline list: [a, 'old', b] hoặc [a, old, b]
        result = result.replace(f"'{old_name}'", f"'{new_name}'")
        result = result.replace(f'"{old_name}"', f'"{new_name}"')

        # Không có nháy trong inline list/rule: , old, hoặc ,old'
        result = re.sub(
            r'(?<=[,\[]\s{0,2})' + re.escape(old_name) + r'(?=\s*[,\]\'])',
            new_name, result
        )

    # ---- Bước 3: Rename group cố định ----
    # Chạy SAU rename_map — thay thế đơn giản bằng replace
    for old_g, new_g in GROUP_RENAMES:
        result = result.replace(old_g, new_g)

    return result


def build_rename_map(decoded_b64: str, yaml_text: str) -> dict:
    rename_map = {}

    for line in decoded_b64.splitlines():
        line = line.strip()
        if "://" in line and "#" in line:
            parts = line.split("#", 1)
            old_name = urllib.parse.unquote(parts[1])
            if not is_info_node(old_name):
                rename_map[old_name] = build_final_name(old_name)

    try:
        y_obj = yaml.safe_load(yaml_text)
        if y_obj and isinstance(y_obj, dict):
            for p in (y_obj.get('proxies') or []):
                n = p.get('name', '')
                if n and not is_info_node(n) and n not in rename_map:
                    rename_map[n] = build_final_name(n)
    except Exception as e:
        print(f"  [!] build_rename_map YAML parse lỗi: {e}")

    return rename_map


def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        print(f"Tổng số link trong DB: {len(links_db)}")
    except Exception as e:
        print(f"Không lấy được links DB: {e}")
        return

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

    print(f"Tổng link gốc cần cào: {len(unique_origins)}")

    for token, orig_url in unique_origins.items():
        print(f"\n-> Token: {token[:8]}...")
        try:
            b64_res = requests.get(orig_url, headers={"User-Agent": "v2rayN/6.23"}, timeout=15)
            yaml_res = requests.get(orig_url, headers={"User-Agent": "ClashForWindows/0.20.39"}, timeout=15)

            if b64_res.status_code != 200:
                print(f"  [!] Base64 HTTP {b64_res.status_code}")
                continue

            print(f"  yaml Content-Type: {yaml_res.headers.get('Content-Type', 'N/A')}")
            print(f"  yaml preview: {yaml_res.text[:80].strip()}")

            b64_content  = b64_res.text.strip()
            yaml_content = yaml_res.text.strip()
            user_info    = b64_res.headers.get("subscription-userinfo", "")

            # Traffic
            traffic_data = {"used": "0.00", "total": "0.00", "percent": 0, "expire": "Vĩnh viễn"}
            if user_info:
                mu = re.search(r'upload=(\d+)',   user_info)
                md = re.search(r'download=(\d+)', user_info)
                mt = re.search(r'total=(\d+)',    user_info)
                me = re.search(r'expire=(\d+)',   user_info)
                up  = int(mu.group(1)) if mu else 0
                dn  = int(md.group(1)) if md else 0
                tot = int(mt.group(1)) if mt else 0
                exp = int(me.group(1)) if me else 0
                used_gb  = (up + dn) / 1_073_741_824
                total_gb = tot / 1_073_741_824
                pct      = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                exp_str  = datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp > 0 else "Vĩnh viễn"
                traffic_data = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": pct, "expire": exp_str}

            # Decode base64 để build rename_map
            padded = b64_content + '=' * ((-len(b64_content)) % 4)
            try:
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  [!] Decode lỗi: {e}")
                decoded = ""

            rename_map = build_rename_map(decoded, yaml_content)
            print(f"  rename_map: {len(rename_map)} entries")

            final_b64 = process_base64(b64_content, rename_map)
            final_b64 = final_b64.replace('\n', '').replace('\r', '').strip()

            # Kiểm tra YAML hợp lệ
            final_yaml = ""
            first_line = yaml_content.split('\n')[0].strip() if yaml_content else ""
            yaml_valid = any(first_line.startswith(k) for k in
                             ['proxies', 'mixed-port', 'port:', 'allow-lan', 'mode:', 'log-level'])

            if yaml_valid:
                final_yaml = process_yaml_raw(yaml_content, rename_map)
                print(f"  [OK] YAML: {len(final_yaml)} chars")
                # Cảnh báo nếu còn chữ Hán
                cn_left = list(set(re.findall(r'[\u4e00-\u9fff]+', final_yaml)))[:5]
                if cn_left:
                    print(f"  [WARN] Còn tên Trung chưa rename: {cn_left}")
            else:
                print(f"  [!] Không phải YAML Clash, bỏ qua.")

            payload = {
                "key":       token,
                "body_b64":  final_b64,
                "body_yaml": final_yaml,
                "info":      user_info,
                "traffic":   traffic_data
            }
            push_res = requests.post(API_PUSH, json=payload, timeout=10)
            print(f"  [OK] Push HTTP {push_res.status_code}")

        except Exception as e:
            print(f"  [!] Lỗi: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    update_all_subs()
