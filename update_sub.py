import requests
import base64
import urllib.parse
import re
import datetime
import yaml

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH  = f"{WORKER_DOMAIN}/api/push_data"

# ============================================================
# BẢNG RENAME GROUP CỐ ĐỊNH
# ============================================================
GROUP_RENAMES = {
    '顶级机场': 'VPN Trinh Hg',
    '良心云':   'VPN Trinh Hg',
    '自动选择': 'Auto Select',
    '故障转移': 'Fallback',
}

# ============================================================
# KEYWORD NHẬN BIẾT DÒNG RÁC (node thông tin, không phải node thật)
# ============================================================
INFO_KEYWORDS = ['剩余流量', '距离下次重置', '套餐到期']


def is_info_node(name: str) -> bool:
    return any(k in name for k in INFO_KEYWORDS)


def clean_text_global(text: str) -> str:
    text = urllib.parse.unquote(text)
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ").replace("台湾", "Taiwan ")
    text = text.replace("🇭🇰香港", "🇭🇰 Hong Kong ").replace("香港", "Hong Kong ")
    text = text.replace("🇸🇬新加坡", "🇸🇬 Singapore ").replace("新加坡", "Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ").replace("日本", "Japan ")
    text = text.replace("🇺🇸美国", "🇺🇸 USA ").replace("美国", "USA ")
    text = text.replace("🇰🇷韩国", "🇰🇷 Korea ").replace("韩国", "Korea ")
    text = text.replace("高速", " High Speed ").replace("专线", " Private ")
    text = text.replace("流媒体", " Streaming").replace("0.1倍", " 0.1x")
    text = text.replace("三网", " TriNet ").replace("顶级机场", "").replace("良心云", "")
    text = re.sub(r'(?i)bgp', '', text)
    text = re.sub(r'[|\-]+', '-', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(" -", "-").replace("- ", "-").replace("-", " - ")
    if text.endswith("-"):
        text = text[:-1].strip()
    return text


def build_final_name(raw_name: str) -> str:
    """Tạo tên cuối cùng từ tên gốc tiếng Trung."""
    clean = clean_text_global(raw_name)
    if clean.startswith("-"):
        clean = clean[1:].strip()
    return f"{clean} - VPN Trinh Hg" if clean else "VPN Trinh Hg"


# ============================================================
# XỬ LÝ BASE64
# ============================================================
def process_base64(content: str, rename_map: dict) -> str:
    """Decode base64, lọc node rác, rename, re-encode."""
    # Pad base64
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
                # Bỏ node rác
                if is_info_node(old_name):
                    continue
                final_name = rename_map.get(old_name, build_final_name(old_name))
                new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    return base64.b64encode("\n".join(new_lines).encode()).decode()


# ============================================================
# XỬ LÝ YAML BẰNG STRING REPLACE (không parse/dump để giữ cấu trúc)
# ============================================================
def process_yaml_raw(yaml_text: str, rename_map: dict) -> str:
    """
    Xử lý YAML trực tiếp trên chuỗi thô.
    - Xóa dòng proxy thông tin (node rác)
    - Rename tên node theo rename_map
    - Rename tên group cố định
    Không dùng yaml.load/dump để tránh mất cấu trúc gốc.
    """
    lines = yaml_text.splitlines()
    filtered = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Phát hiện proxy entry dạng inline: "  - { name: '...', ... }"
        if re.match(r'^\s*-\s*\{', line):
            # Kiểm tra nếu dòng này chứa node rác
            if any(k in line for k in INFO_KEYWORDS):
                i += 1
                continue
            filtered.append(line)
            i += 1
            continue

        # Phát hiện proxy entry dạng block: "  - name: ..."
        if re.match(r'^\s*-\s+name:', line):
            name_match = re.search(r"name:\s*['\"]?(.+?)['\"]?\s*$", line)
            if name_match:
                raw_name = name_match.group(1).strip().strip("'\"")
                if is_info_node(raw_name):
                    # Bỏ qua cả block proxy này (các dòng tiếp theo thụt lề sâu hơn)
                    i += 1
                    while i < len(lines):
                        next_stripped = lines[i].strip()
                        # Dòng tiếp theo vẫn là thuộc tính của proxy này
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

    # --- Rename theo rename_map ---
    # Sắp xếp theo độ dài giảm dần để tránh replace nhầm tên ngắn hơn trước
    sorted_map = sorted(rename_map.items(), key=lambda x: len(x[0]), reverse=True)

    for old_name, new_name in sorted_map:
        if not old_name:
            continue
        # Thay thế các dạng xuất hiện phổ biến trong YAML
        result = result.replace(f"name: '{old_name}'", f"name: '{new_name}'")
        result = result.replace(f'name: "{old_name}"', f'name: "{new_name}"')
        result = result.replace(f"name: {old_name}\n", f"name: {new_name}\n")
        result = result.replace(f"name: {old_name}\r", f"name: {new_name}\r")
        # Trong danh sách proxies của group: '老名字' hoặc "老名字"
        result = result.replace(f"'{old_name}'", f"'{new_name}'")
        result = result.replace(f'"{old_name}"', f'"{new_name}"')
        # Không có nháy (cẩn thận với word boundary)
        result = re.sub(
            r'(?<![\'"\w\u4e00-\u9fff])' + re.escape(old_name) + r'(?![\'"\w\u4e00-\u9fff])',
            new_name,
            result
        )

    # --- Rename group cố định ---
    for old_g, new_g in GROUP_RENAMES.items():
        result = result.replace(old_g, new_g)

    return result


# ============================================================
# BUILD RENAME MAP TỪ BASE64 VÀ YAML
# ============================================================
def build_rename_map(decoded_b64: str, yaml_text: str) -> dict:
    rename_map = {}

    # Từ base64
    for line in decoded_b64.splitlines():
        line = line.strip()
        if "://" in line and "#" in line:
            parts = line.split("#", 1)
            old_name = urllib.parse.unquote(parts[1])
            if is_info_node(old_name):
                continue
            rename_map[old_name] = build_final_name(old_name)

    # Bổ sung từ YAML (một số node chỉ có trong YAML)
    try:
        y_obj = yaml.safe_load(yaml_text)
        if y_obj and isinstance(y_obj, dict) and 'proxies' in y_obj:
            for p in y_obj.get('proxies', []):
                n = p.get('name', '')
                if n and not is_info_node(n) and n not in rename_map:
                    rename_map[n] = build_final_name(n)
    except Exception as e:
        print(f"  [!] Không thể parse YAML để build rename_map: {e}")

    return rename_map


# ============================================================
# HÀM CHÍNH
# ============================================================
def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        print(f"Tổng số link trong DB: {len(links_db)}")
    except Exception as e:
        print(f"Không lấy được links DB: {e}")
        return

    # Chỉ fetch link GỐC duy nhất (không fetch link ẩn/phụ)
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
        print(f"\n-> Đang xử lý Token gốc: {token[:8]}...")
        try:
            # Fetch base64 (dành cho v2rayN, NekoBox, v.v.)
            b64_res = requests.get(
                orig_url,
                headers={"User-Agent": "v2rayN/6.23"},
                timeout=15
            )
            # Fetch YAML (dành cho Clash)
            yaml_res = requests.get(
                orig_url,
                headers={"User-Agent": "ClashForWindows/0.20.39"},
                timeout=15
            )

            if b64_res.status_code != 200:
                print(f"  [!] Base64 fetch thất bại: HTTP {b64_res.status_code}")
                continue

            # --- Debug: kiểm tra server trả đúng định dạng không ---
            print(f"  b64 Content-Type : {b64_res.headers.get('Content-Type', 'N/A')}")
            print(f"  yaml Content-Type: {yaml_res.headers.get('Content-Type', 'N/A')}")
            print(f"  yaml preview     : {yaml_res.text[:80].strip()}")

            b64_content  = b64_res.text.strip()
            yaml_content = yaml_res.text.strip()
            user_info    = b64_res.headers.get("subscription-userinfo", "")

            # --- Tính traffic ---
            traffic_data = {
                "used": "0.00", "total": "0.00",
                "percent": 0,   "expire": "Vĩnh viễn"
            }
            if user_info:
                mu  = re.search(r'upload=(\d+)',   user_info)
                md  = re.search(r'download=(\d+)', user_info)
                mt  = re.search(r'total=(\d+)',    user_info)
                me  = re.search(r'expire=(\d+)',   user_info)
                up  = int(mu.group(1)) if mu else 0
                dn  = int(md.group(1)) if md else 0
                tot = int(mt.group(1)) if mt else 0
                exp = int(me.group(1)) if me else 0
                used_gb  = (up + dn) / 1_073_741_824
                total_gb = tot / 1_073_741_824
                pct      = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                exp_str  = (datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y')
                            if exp > 0 else "Vĩnh viễn")
                traffic_data = {
                    "used":    f"{used_gb:.2f}",
                    "total":   f"{total_gb:.2f}",
                    "percent": pct,
                    "expire":  exp_str
                }

            # --- Decode base64 để build rename_map ---
            missing = len(b64_content) % 4
            if missing:
                b64_content += '=' * (4 - missing)
            try:
                decoded = base64.b64decode(b64_content).decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  [!] Không decode được base64: {e}")
                decoded = ""

            rename_map = build_rename_map(decoded, yaml_content)
            print(f"  rename_map có {len(rename_map)} entry")

            # --- Xử lý base64 ---
            final_b64 = process_base64(b64_content, rename_map)
            final_b64 = final_b64.replace('\n', '').replace('\r', '').strip()

            # --- Xử lý YAML ---
            final_yaml = ""
            if yaml_content and yaml_content.startswith(('proxies', 'mixed-port', 'port', 'allow')):
                # Server trả đúng YAML
                final_yaml = process_yaml_raw(yaml_content, rename_map)
                print(f"  [OK] YAML đã xử lý ({len(final_yaml)} chars)")
            else:
                print(f"  [!] Server không trả YAML Clash, bỏ qua body_yaml")

            # --- Push lên KV ---
            payload = {
                "key":      token,
                "body_b64": final_b64,
                "body_yaml": final_yaml,
                "info":     user_info,
                "traffic":  traffic_data
            }
            push_res = requests.post(API_PUSH, json=payload, timeout=10)
            print(f"  [OK] Push thành công → HTTP {push_res.status_code}")

        except Exception as e:
            print(f"  [!] Lỗi khi xử lý token {token[:8]}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    update_all_subs()
