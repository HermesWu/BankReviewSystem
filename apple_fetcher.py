# apple_fetcher.py
import requests
import pandas as pd

def get_apple_data(app_id="422844108", days_limit=7, start_from_date=None):
    print(f"🍎 启动 Apple 渠道采集 (静默抓取, 智能增量版)...")
    raw_reviews = []
    
    # 设定时间边界兜底
    backup_threshold = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days_limit)
    
    # 🌟 增量核心：确认 Apple 的截止线
    if start_from_date is not None:
        threshold_date = pd.to_datetime(start_from_date).tz_localize('UTC') # Apple数据带UTC时区
        print(f"🛡️ [增量线激活] Apple 抓取遇到日期小或等于 {threshold_date.strftime('%Y-%m-%d')} 将立刻收工。")
    else:
        threshold_date = backup_threshold.tz_localize('UTC')
        print(f"📅 [全量回溯激活] 本地无 Apple 历史记录，默认回溯近 {days_limit} 天。")
    
    for page in range(1, 11): 
        url = f"https://itunes.apple.com/cn/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        try:
            # 伪装请求头，防止静默被封
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=10)
            entries = res.json().get('feed', {}).get('entry', [])
            if not entries or len(entries) <= 1: break
                
            for entry in entries[1:]:
                updated_str = entry.get('updated', {}).get('label')
                review_time = pd.to_datetime(updated_str, utc=True)
                
                # 🌟 真正的增量熔断：只要遇到库里存在的老时间，直接 return 结束所有翻页！
                if review_time <= threshold_date:
                    print(f"  🛑 [Apple 增量熔断触发] 检测到已存在历史记录 ({review_time.strftime('%Y-%m-%d')})，光速收兵！")
                    return raw_reviews

                # 对齐本地时间入库
                local_time = review_time.tz_localize(None)
                raw_reviews.append({
                    "来源": "App Store",
                    "日期": local_time.strftime('%Y-%m-%d'),
                    "具体时间": local_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "标题": entry.get('title', {}).get('label', '无标题'),
                    "内容": entry.get('content', {}).get('label', '无内容'),
                    "评分": int(entry.get('im:rating', {}).get('label', 0))
                })
        except Exception as e:
            print(f"  ❌ Apple 第 {page} 页异常: {e}")
            break

    return raw_reviews