# myapp_spider.py
from playwright.sync_api import sync_playwright
import pandas as pd
import re
import time  

def get_myapp_data(pkg_name="com.ecitic.bank.mobile", days_limit=14, start_from_date=None):
    print(f"🚀 启动应用宝采集 (智能增量 + 12秒错峰版)...")
    print("⏳ 应用宝主动避让，沉睡 12 秒，确保华为独占 CPU 完成滑动破门...")
    time.sleep(12)

    raw_reviews = []
    now = pd.Timestamp.now().tz_localize(None)
    backup_threshold = now - pd.Timedelta(days=days_limit)
    
    # 🌟 增量截止线判定
    if start_from_date is not None:
        threshold_date = pd.to_datetime(start_from_date).tz_localize(None)
        print(f"🛡️ [增量线激活] 应用宝抓取遇到日期小或等于 {threshold_date.strftime('%Y-%m-%d')} 的评论将立刻收工。")
    else:
        threshold_date = backup_threshold
        print(f"📅 [全量回溯激活] 本地无历史记录，默认回溯近 {days_limit} 天。")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            executable_path='/root/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome',
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = browser.new_page()
        
        try:
            url = f"https://sj.qq.com/appdetail/{pkg_name}/review?tab=10000"
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)
            
            for _ in range(6):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    if re.search(r'comment|review|reply', class_name, re.IGNORECASE) and \
                       not re.search(r'list|container|wrapper|section|group|box|header|footer|date|info', class_name, re.IGNORECASE):
                        
                        raw_text = div.inner_text()
                        if not raw_text or len(raw_text) < 15: continue
                            
                        text_clean_for_check = raw_text.replace('\n', ' ')
                        if "全部" in text_clean_for_check and "最新" in text_clean_for_check and "好评" in text_clean_for_check: continue
                        if "人评分" in text_clean_for_check: continue
                        if len(re.findall(r'202\d', text_clean_for_check)) > 2: continue
                        
                        date_match = re.search(r'(202\d)[-/\.年](\d{1,2})[-/\.月](\d{1,2})', text_clean_for_check)
                        short_date_match = re.search(r'(?<!\d)(\d{1,2})[-/月](\d{1,2})[日]?(?!\d)', text_clean_for_check)
                        
                        review_date = None
                        try:
                            if date_match:
                                y, m, d = date_match.groups()
                                review_date = pd.to_datetime(f"{y}-{m}-{d}")
                            elif "刚刚" in raw_text or "分钟前" in raw_text or "小时前" in raw_text or "今天" in raw_text:
                                review_date = now
                            elif "昨天" in raw_text:
                                review_date = now - pd.Timedelta(days=1)
                            elif "前天" in raw_text:
                                review_date = now - pd.Timedelta(days=2)
                            elif short_date_match:
                                m, d = short_date_match.groups()
                                current_year = now.year
                                review_date = pd.to_datetime(f"{current_year}-{m}-{d}")
                                if review_date > now: review_date = pd.to_datetime(f"{current_year - 1}-{m}-{d}")
                        except Exception: continue 
                        
                        if review_date:
                            # 🌟 核心增量逻辑：一旦踩线，光速闪人
                            if review_date <= threshold_date: 
                                print(f"  🛑 [应用宝增量熔断] 检测到已存在历史评论 ({review_date.strftime('%Y-%m-%d')})，停止解析更早数据！")
                                break 
                                
                            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                            pure_content_lines = []
                            for line in lines:
                                if re.search(r'202\d', line) or re.search(r'^\d+$', line) or '***' in line: continue
                                pure_content_lines.append(line)
                                
                            final_content = " | ".join(pure_content_lines)
                            pure_text_test = re.sub(r'[\d\|\s\-:/\.\|_]', '', final_content)
                            if len(pure_text_test) < 3: continue

                            date_str = review_date.strftime('%Y-%m-%d')
                            raw_reviews.append({
                                "来源": "腾讯应用宝", "日期": date_str, "具体时间": date_str + " 00:00:00",
                                "标题": "无标题", "内容": final_content, "评分": 0
                            })
                            print(f"  [✅ 数据入库] 提取最新应用宝评价: {date_str} - {final_content[:20]}...")
                except Exception: continue
        except Exception as e: print(f"❌ 应用宝抓取异常: {e}")
        finally: browser.close()
            
    return [dict(t) for t in {tuple(d.items()) for d in raw_reviews}]