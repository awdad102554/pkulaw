#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北大法宝高级检索页面信息爬取
用于登录并获取高级检索页面的 HTML 结构，方便后续分析字段、按钮和操作流程

使用方法:
    python 北大法宝高级检索页面信息爬取.py
"""

import re
import time
import random
import os
import sys

# 把当前目录加入路径，方便 import 主爬虫类
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 北大法宝图书馆自动爬虫 import PkulawCrawler, print_info, print_success, print_error, print_step, print_warning


class AdvancedSearchCrawler(PkulawCrawler):
    def wait(self, min_sec=2, max_sec=5):
        """随机等待"""
        sec = random.randint(min_sec, max_sec)
        print_info(f"等待 {sec} 秒...")
        time.sleep(sec)
    
    def save_page_html(self, url, filename):
        """访问指定URL并保存页面HTML"""
        try:
            print_info(f"访问: {url}")
            self.pkulaw_page.get(url)
            time.sleep(5)  # 等待页面完全加载（高级检索页面字段较多）
            
            html = self.pkulaw_page.html
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            print_success(f"页面HTML已保存: {filepath} ({len(html)} 字符)")
            return True
        except Exception as e:
            print_error(f"保存页面失败: {e}")
            return False


def main():
    print_step(0, "北大法宝高级检索页面信息爬取")
    print_info("本脚本将登录图书馆 → 跳转北大法宝 → 访问高级检索页面 → 保存HTML")
    print()
    
    crawler = AdvancedSearchCrawler()
    
    try:
        # 1. 连接浏览器
        if not crawler.init_browser():
            print_error("连接浏览器失败")
            return
        
        # 2. 登录图书馆
        if not crawler.login_library():
            print_error("登录失败")
            return
        
        crawler.wait()
        
        # 3. 跳转北大法宝
        if not crawler.goto_pkulaw():
            print_error("跳转北大法宝失败")
            return
        
        crawler.wait()
        
        # 获取当前北大法宝的基础代理URL
        current_url = crawler.pkulaw_page.url
        match = re.match(r'(https?://[^/]+)', current_url)
        if match:
            base_url = match.group(1)
        else:
            base_url = current_url.rstrip('/')
        
        print_info(f"当前北大法宝基础URL: {base_url}")
        print()
        
        # 4. 爬取两个高级检索页面
        print_step(5, "开始爬取高级检索页面HTML")
        
        # 司法案例高级检索
        case_url = base_url + '/advanced/case/pfnl'
        crawler.save_page_html(case_url, 'advanced_case_pfnl.html')
        
        crawler.wait(3, 5)
        
        # 法律法规高级检索
        law_url = base_url + '/advanced/law/chl'
        crawler.save_page_html(law_url, 'advanced_law_chl.html')
        
        print()
        print_success("所有页面爬取完成！")
        print_info("生成的文件:")
        print_info("  - advanced_case_pfnl.html  (司法案例高级检索)")
        print_info("  - advanced_law_chl.html    (法律法规高级检索)")
        
    except KeyboardInterrupt:
        print("\n已中止")
    except Exception as e:
        print_error(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        crawler.close_browser()
        print()
        input("按回车键退出...")


if __name__ == '__main__':
    main()
