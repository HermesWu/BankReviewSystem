# huawei_spider.py
from playwright.sync_api import sync_playwright
import pandas as pd
import re
import base64

def get_huawei_data(app_id="C10350054", days_limit=30, start_from_date=None):
    print(f"🚀 启动华为渠道采集 (主动雷达轮询 + 智能增量版)...")
    raw_reviews = []
    
    # 计算时间兜底线
    backup_threshold = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(days=days_limit)
    
    # 🌟 增量核心时间线确定
    if start_from_date is not None:
        threshold_date = pd.to_datetime(start_from_date).tz_localize(None)
        print(f"🛡️ [增量线激活] 抓取遇到日期小或等于 {threshold_date.strftime('%Y-%m-%d')} 的评论将立刻收工。")
    else:
        threshold_date = backup_threshold
        print(f"📅 [全量回溯激活] 本地无历史记录，默认回溯近 {days_limit} 天。")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            executable_path='/root/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome',
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        # 保持巨型视野，但稍微下调到 8000，防止 Chromium 内存偶发渲染故障
        page = browser.new_page(viewport={'width': 1920, 'height': 8000})
        
        try:
            url = f"https://appgallery.huawei.com/app/{app_id}"
            page.goto(url, timeout=60000)
            
            # 🌟 核心升级：废弃死等，换用“主动雷达轮询”
            print("⏬ 启动【雷达轮询】扫描，完美容忍网络延迟抖动...")
            clicked = False
            
            # 连续扫描 12 次，每次间隔 1.5 秒（最高容忍 18 秒的极度网络卡顿）
            for i in range(12):
                try:
                    # 每次扫描前，强行用原生 JS 往下抖一下，逼迫 Vue 框架更新
                    page.evaluate("window.scrollBy(0, 500)")
                    
                    btn = page.locator(".pcscorecommentlistcard .more").first
                    if btn.count() > 0:
                        btn.evaluate("node => node.click()")
                        page.wait_for_timeout(3000) # 点完之后等动画展开
                        print(f"✅ 第 {i+1} 次雷达扫描：成功锁定目标并破门！")
                        clicked = True
                        break 
                except:
                    pass
                
                # 没找到就等 1.5 秒再扫下一次
                page.wait_for_timeout(1500)
            
            if not clicked:
                print("⚠️ 致命警告：雷达苦等 18 秒仍未见按钮，可能遭到风控或网络彻底断连，放弃本次采集！")
                return []

            print("🔄 正在详情页深挖加载新评论...")
            for _ in range(6):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    if re.search(r'comment|review', class_name, re.IGNORECASE) and \
                       not re.search(r'list|container|wrapper|section|group|box', class_name, re.IGNORECASE):
                       
                        text = div.inner_text()
                        if not text or len(text) < 15: continue
                        
                        html_content = div.inner_html()
                        review_score = 0
                        star_box_match = re.search(r'class="[^"]*newStarBox[^"]*"[^>]*>(.*?)</div>', html_content, re.IGNORECASE | re.DOTALL)
                        if star_box_match:
                            box_html = star_box_match.group(1)
                            img_b64_list = re.findall(r'src="data:image/svg\+xml;base64,([^"]+)"', box_html)
                            for b64_str in img_b64_list:
                                try:
                                    svg_text = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                                    if 'FDC51E' in svg_text.upper(): review_score += 1
                                except: pass

                        text_clean = text.replace('\n', ' | ')
                        if "查看全部" in text_clean and "人评分" in text_clean: continue
                        
                        date_match_A = re.search(r'(202\d)[-/\.年](\d{1,2})[-/\.月](\d{1,2})', text_clean)
                        date_match_B = re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})/(202\d)', text_clean)
                        
                        review_date = None
                        if date_match_A:
                            y, m, d = date_match_A.groups()
                            review_date = pd.to_datetime(f"{y}-{m}-{d}")
                        elif date_match_B:
                            m, d, y = date_match_B.groups()
                            review_date = pd.to_datetime(f"{y}-{m}-{d}")
                        
                        if review_date:
                            # 🌟 完美保留增量熔断机制
                            if review_date <= threshold_date: 
                                print(f"  🛑 [增量同步熔断触发] 检测到已存在历史记录 ({review_date.strftime('%Y-%m-%d')})，光速收兵！")
                                break 
                                
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            pure_content_lines = []
                            for line in lines:
                                if '***' in line: continue
                                if re.search(r'202\d', line) or re.search(r'^\(?\d+\.\d+\.\d+\)?$', line): continue
                                pure_content_lines.append(line)
                                
                            final_content = " ".join(pure_content_lines)
                            if not final_content: continue

                            date_str = review_date.strftime('%Y-%m-%d')
                            raw_reviews.append({
                                "来源": "华为市场", "日期": date_str, "具体时间": date_str + " 00:00:00",
                                "标题": "无标题", "内容": final_content, "评分": review_score
                            })
                except Exception: continue
        except Exception as e: print(f"❌ 华为抓取异常: {e}")
        finally: browser.close() 
            
    return [dict(t) for t in {tuple(d.items()) for d in raw_reviews}]