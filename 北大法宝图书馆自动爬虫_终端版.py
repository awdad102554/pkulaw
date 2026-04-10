#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北大法宝图书馆自动爬虫 - 天津大学版（终端版）
无需GUI，直接在终端显示日志和流程

使用方法:
    python 北大法宝图书馆自动爬虫_终端版.py
"""

from DrissionPage import Chromium, ChromiumPage
import time
import random
import os
import sys
import re
from datetime import datetime

# ============== 配置区域 ==============
# 天津大学图书馆配置
LIBRARY_URL = 'https://eds.tju.edu.cn/ermsClient/browse.do'
LIBRARY_ACCOUNT = '017656'
LIBRARY_PASSWORD = 'Lhy740220'

# Chrome调试端口
CHROME_PORT = '127.0.0.1:9333'

# 等待时间区间（秒）
MIN_WAIT_TIME = 2
MAX_WAIT_TIME = 5

# 默认搜索参数
DEFAULT_KEYWORD = ''
DEFAULT_CASE_TYPE = ''  # 民事案件/刑事案件/行政案件/执行案件/知识产权
DEFAULT_YEAR = ''
DEFAULT_COURT = ''
DEFAULT_MAX_PAGES = 5

# ============== 颜色输出工具 ==============
class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """打印标题"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def print_step(step_num, text):
    """打印步骤"""
    print(f"{Colors.CYAN}[步骤 {step_num}]{Colors.ENDC} {Colors.BOLD}{text}{Colors.ENDC}")

def print_info(text):
    """打印信息"""
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {text}")

def print_success(text):
    """打印成功"""
    print(f"{Colors.GREEN}[✓ SUCCESS]{Colors.ENDC} {text}")

def print_warning(text):
    """打印警告"""
    print(f"{Colors.YELLOW}[⚠ WARNING]{Colors.ENDC} {text}")

def print_error(text):
    """打印错误"""
    print(f"{Colors.RED}[✗ ERROR]{Colors.ENDC} {text}")

def print_progress(current, total, text=""):
    """打印进度条"""
    percent = int((current / total) * 100) if total > 0 else 0
    bar_length = 40
    filled = int(bar_length * percent / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} {percent}% ({current}/{total}) {text}", end='', flush=True)
    if current == total:
        print()  # 换行

def input_text(prompt, default=""):
    """获取用户输入"""
    if default:
        user_input = input(f"{Colors.YELLOW}[INPUT]{Colors.ENDC} {prompt} (默认: {default}): ").strip()
        return user_input if user_input else default
    else:
        return input(f"{Colors.YELLOW}[INPUT]{Colors.ENDC} {prompt}: ").strip()

def input_yes_no(prompt, default=True):
    """获取是/否输入"""
    default_str = "Y/n" if default else "y/N"
    user_input = input(f"{Colors.YELLOW}[INPUT]{Colors.ENDC} {prompt} ({default_str}): ").strip().lower()
    if not user_input:
        return default
    return user_input in ['y', 'yes', '是', 'true']

# ============== 爬虫核心类 ==============
class PkulawLibraryCrawler:
    """北大法宝图书馆自动爬虫"""
    
    def __init__(self):
        # 文件路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.urls_file = os.path.join(base_dir, 'urls.txt')
        self.folder_path = os.path.join(base_dir, 'downloads')
        
        # 爬虫状态
        self.state = 1
        self.browser = None
        self.page = None
        self.pkulaw_page = None
        
        # 统计信息
        self.stats = {
            'urls_collected': 0,
            'urls_downloaded': 0,
            'errors': 0
        }
        
        # 确保目录存在
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            print_info(f"创建下载目录: {self.folder_path}")
    
    def init_browser(self):
        """初始化浏览器连接"""
        print_info("正在连接到Chrome浏览器...")
        try:
            self.browser = Chromium(CHROME_PORT)
            self.page = self.browser.latest_tab
            print_success(f"已连接到浏览器，当前页面: {self.page.title}")
            return True
        except Exception as e:
            print_error(f"连接浏览器失败: {e}")
            print_warning("请确保Chrome已启动调试模式: chrome.exe --remote-debugging-port=9333")
            return False
    
    def wait_random(self):
        """随机等待"""
        wait_time = random.randint(MIN_WAIT_TIME, MAX_WAIT_TIME)
        print_info(f"等待 {wait_time} 秒...")
        time.sleep(wait_time)
    
    def login_library(self):
        """登录天津大学图书馆"""
        print_step(1, "登录天津大学图书馆")
        
        try:
            # 访问图书馆网站
            print_info(f"访问: {LIBRARY_URL}")
            self.page.get(LIBRARY_URL)
            time.sleep(3)
            
            print_info(f"当前页面标题: {self.page.title}")
            
            # 尝试查找登录入口
            login_found = False
            
            # 尝试点击校外访问或登录链接
            try:
                login_link = self.page.ele('text:校外访问', timeout=3)
                if login_link:
                    print_info("找到校外访问入口")
                    login_link.click()
                    time.sleep(2)
                    login_found = True
            except:
                pass
            
            if not login_found:
                try:
                    login_link = self.page.ele('text:登录', timeout=2)
                    if login_link:
                        print_info("找到登录入口")
                        login_link.click()
                        time.sleep(2)
                        login_found = True
                except:
                    pass
            
            # 填写账号密码
            print_info("正在填写登录信息...")
            
            # 账号输入框
            account_input = None
            for selector in ['tag:input@name=account', 'tag:input@name=username', 'tag:input@id=account', 
                            'tag:input@id=username', 'tag:input@placeholder*=账号', 'tag:input@placeholder*=学号']:
                try:
                    account_input = self.page.ele(selector, timeout=2)
                    if account_input:
                        break
                except:
                    continue
            
            if not account_input:
                print_error("未找到账号输入框")
                # 尝试截图查看页面结构
                self.save_debug_html("login_page")
                return False
            
            account_input.clear()
            account_input.input(LIBRARY_ACCOUNT)
            print_info(f"已填写账号: {LIBRARY_ACCOUNT}")
            
            # 密码输入框
            password_input = None
            for selector in ['tag:input@name=password', 'tag:input@type=password', 'tag:input@id=password']:
                try:
                    password_input = self.page.ele(selector, timeout=2)
                    if password_input:
                        break
                except:
                    continue
            
            if not password_input:
                print_error("未找到密码输入框")
                return False
            
            password_input.clear()
            password_input.input(LIBRARY_PASSWORD)
            print_info("已填写密码")
            
            # 点击登录
            try:
                submit_btn = self.page.ele('tag:button@type=submit', timeout=2)
                submit_btn.click()
            except:
                try:
                    submit_btn = self.page.ele('text:登录', timeout=2)
                    submit_btn.click()
                except:
                    password_input.input('\n')  # 按回车
            
            print_info("已提交登录，等待跳转...")
            time.sleep(5)
            
            # 检查登录结果
            current_url = self.page.url
            page_title = self.page.title
            
            if 'login' in current_url.lower() or 'error' in current_url.lower():
                print_error("登录失败，请检查账号密码")
                return False
            else:
                print_success(f"图书馆登录成功！当前页面: {page_title}")
                return True
                
        except Exception as e:
            print_error(f"登录过程出错: {e}")
            return False
    
    def goto_pkulaw(self, search_params=None):
        """跳转到北大法宝"""
        print_step(2, "跳转到北大法宝")
        
        try:
            print_info("在图书馆页面查找北大法宝链接...")
            
            # 查找北大法宝链接
            pkulaw_link = None
            
            # 通过文本查找
            try:
                pkulaw_link = self.page.ele('text:北大法宝', timeout=3)
            except:
                pass
            
            if not pkulaw_link:
                try:
                    pkulaw_link = self.page.ele('text:法宝', timeout=2)
                except:
                    pass
            
            # 通过链接查找
            if not pkulaw_link:
                links = self.page.eles('tag:a')
                for link in links:
                    href = link.attr('href') or ''
                    text = link.text or ''
                    if 'pkulaw' in href.lower() or '法宝' in text:
                        pkulaw_link = link
                        print_info(f"找到链接: {text}")
                        break
            
            if pkulaw_link:
                pkulaw_link.click()
                print_info("已点击北大法宝链接，等待跳转...")
                time.sleep(5)
            else:
                print_warning("未找到北大法宝链接，尝试直接访问...")
                self.page.get('https://www.pkulaw.com/')
                time.sleep(3)
            
            # 获取北大法宝标签页
            time.sleep(2)
            tabs = self.browser.get_tabs()
            
            for tab in tabs:
                try:
                    if 'pkulaw' in tab.url:
                        self.pkulaw_page = tab
                        print_info(f"已找到北大法宝标签页: {tab.title}")
                        break
                except:
                    continue
            
            if not self.pkulaw_page:
                self.pkulaw_page = self.browser.latest_tab
                print_info(f"使用最新标签页: {self.pkulaw_page.title}")
            
            # 如果有搜索参数，构建URL
            if search_params:
                param_list = []
                if search_params.get('keyword'):
                    param_list.append(f"keyword={search_params['keyword']}")
                if search_params.get('case_type'):
                    param_list.append(f"case_type={search_params['case_type']}")
                if search_params.get('year'):
                    param_list.append(f"year={search_params['year']}")
                
                if param_list:
                    full_url = f"https://www.pkulaw.com/chl?{'&'.join(param_list)}"
                    print_info(f"访问带参数链接...")
                    self.pkulaw_page.get(full_url)
                    time.sleep(3)
            
            print_success(f"已进入北大法宝: {self.pkulaw_page.title}")
            return True
            
        except Exception as e:
            print_error(f"跳转北大法宝出错: {e}")
            return False
    
    def search_cases(self, keyword='', case_type='', year='', court=''):
        """搜索案件"""
        print_step(3, "搜索案件")
        
        try:
            page = self.pkulaw_page
            
            print_info(f"搜索条件: 关键词={keyword}, 类型={case_type}, 年份={year}, 法院={court}")
            
            # 查找搜索框
            search_input = None
            for selector in ['tag:input@id=keyword', 'tag:input@name=keyword', 'tag:input@placeholder*=搜索']:
                try:
                    search_input = page.ele(selector, timeout=2)
                    if search_input:
                        break
                except:
                    continue
            
            if search_input and keyword:
                search_input.clear()
                search_input.input(keyword)
                print_info(f"已输入关键词: {keyword}")
                time.sleep(1)
            
            # 点击搜索
            try:
                search_btn = page.ele('tag:button@type=submit', timeout=2)
                if not search_btn:
                    search_btn = page.ele('text:搜索', timeout=2)
                
                if search_btn:
                    search_btn.click()
                    print_info("已点击搜索按钮")
                else:
                    if search_input:
                        search_input.input('\n')
                        print_info("已按回车搜索")
            except:
                pass
            
            time.sleep(5)
            print_info(f"当前页面: {page.title}")
            
            # 尝试获取结果数量
            try:
                result_count = page.ele('.result-count', timeout=3).text
                print_success(f"搜索结果: {result_count}")
            except:
                pass
            
            return True
            
        except Exception as e:
            print_error(f"搜索案件出错: {e}")
            return False
    
    def collect_urls(self, max_pages=5):
        """收集URL"""
        print_step(4, f"收集案件URL (最多{max_pages}页)")
        
        try:
            page = self.pkulaw_page
            existing_urls = self.read_urls_from_file()
            total_new = 0
            
            for page_num in range(1, max_pages + 1):
                if self.state == 0:
                    print_warning("用户中断操作")
                    break
                
                print_info(f"正在处理第 {page_num} 页...")
                
                # 获取列表元素
                target = None
                for selector in ['tag:tbody', '.result-list', '.list-content', '.search-result']:
                    try:
                        target = page.ele(selector, timeout=2)
                        if target:
                            break
                    except:
                        continue
                
                if not target:
                    print_warning("未找到列表元素")
                    break
                
                # 获取行元素
                items = target.eles('tag:tr')
                if not items:
                    items = target.eles('.list-item')
                if not items:
                    items = target.eles('tag:li')
                
                if not items:
                    print_warning("本页未找到案件条目")
                    break
                
                print_info(f"本页找到 {len(items)} 个条目")
                
                page_new = 0
                for i, item in enumerate(items):
                    try:
                        link_ele = item.ele('tag:a')
                        if link_ele:
                            url = link_ele.attr('href')
                            title = link_ele.text or ''
                            
                            if url:
                                # 补全URL
                                if url.startswith('/'):
                                    url = 'https://www.pkulaw.com' + url
                                elif not url.startswith('http'):
                                    url = 'https://www.pkulaw.com/' + url
                                
                                if url not in existing_urls:
                                    existing_urls.add(url)
                                    self.append_url_to_file(url)
                                    page_new += 1
                                    total_new += 1
                        
                        print_progress(i + 1, len(items), f"收集: {title[:20]}..." if title else "")
                        
                    except Exception as e:
                        continue
                
                print_success(f"第 {page_num} 页收集完成，新增 {page_new} 个URL")
                
                # 翻页
                if page_num < max_pages:
                    try:
                        next_btn = None
                        for selector in ['text:下一页', '.next', '.pagination-next']:
                            try:
                                next_btn = page.ele(selector, timeout=2)
                                if next_btn:
                                    break
                            except:
                                continue
                        
                        if next_btn:
                            btn_class = next_btn.attr('class') or ''
                            if 'disabled' not in btn_class and '禁' not in btn_class:
                                next_btn.click()
                                print_info("正在翻页...")
                                time.sleep(3)
                            else:
                                print_info("已到达最后一页")
                                break
                        else:
                            print_info("未找到下一页按钮")
                            break
                            
                    except Exception as e:
                        print_warning(f"翻页出错: {e}")
                        break
            
            self.stats['urls_collected'] = total_new
            print_success(f"URL收集完成，共新增 {total_new} 个URL")
            return True
            
        except Exception as e:
            print_error(f"收集URL出错: {e}")
            return False
    
    def download_content(self):
        """下载内容"""
        print_step(5, "下载案件内容")
        
        try:
            urls = self.read_urls_from_file()
            
            if not urls:
                print_warning("没有URL需要下载")
                return False
            
            total = len(urls)
            print_info(f"共有 {total} 个案件等待下载")
            
            page = self.pkulaw_page if self.pkulaw_page else self.browser.new_tab()
            
            success_count = 0
            failed_count = 0
            
            for i, url in enumerate(list(urls)[:10000]):  # 限制数量
                if self.state == 0:
                    print_warning("用户中断下载")
                    break
                
                try:
                    # 等待
                    self.wait_random()
                    
                    # 访问页面
                    page.get(url)
                    time.sleep(2)
                    
                    # 获取内容
                    title = ""
                    content = ""
                    
                    try:
                        fulltext_wrap = page.ele('.fulltext-wrap')
                        title = fulltext_wrap.ele('.title').text
                        content = fulltext_wrap.ele('.content').text
                    except:
                        try:
                            title = page.ele('.title').text
                            content = page.ele('.fulltext').text
                        except:
                            title = page.title
                            content = page.html
                    
                    # 处理文件名
                    for c in "*?:<>|/\\":
                        title = title.replace(c, '某')
                    
                    # 保存文件
                    file_path = os.path.join(self.folder_path, f'{title}.txt')
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # 删除已下载的URL
                    self.remove_url_from_file(url)
                    success_count += 1
                    
                    print_progress(i + 1, total, f"下载: {title[:25]}...")
                    
                except Exception as e:
                    failed_count += 1
                    print_error(f"下载失败: {e}")
                    if "timeout" in str(e).lower() or "无法连接" in str(e):
                        print_error("网络问题，中断下载")
                        break
            
            self.stats['urls_downloaded'] = success_count
            remaining = len(self.read_urls_from_file())
            print_success(f"下载完成: 成功 {success_count}, 失败 {failed_count}, 剩余 {remaining}")
            return True
            
        except Exception as e:
            print_error(f"下载过程出错: {e}")
            return False
    
    def read_urls_from_file(self):
        """读取URL"""
        urls = set()
        if os.path.exists(self.urls_file):
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        urls.add(url)
        return urls
    
    def append_url_to_file(self, url):
        """追加URL"""
        with open(self.urls_file, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
    
    def remove_url_from_file(self, url_to_remove):
        """删除URL"""
        urls = self.read_urls_from_file()
        urls.discard(url_to_remove)
        with open(self.urls_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')
    
    def save_debug_html(self, filename):
        """保存调试HTML"""
        try:
            html = self.page.html
            debug_file = os.path.join(self.folder_path, f'debug_{filename}_{int(time.time())}.html')
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print_info(f"调试文件已保存: {debug_file}")
        except:
            pass
    
    def run_full_auto(self, keyword='', case_type='', year='', court='', max_pages=5):
        """运行全自动流程"""
        print_header("北大法宝图书馆自动爬虫启动")
        
        start_time = time.time()
        
        # 1. 初始化浏览器
        if not self.init_browser():
            return False
        
        # 2. 登录图书馆
        if not self.login_library():
            print_error("登录失败，流程中止")
            return False
        
        self.wait_random()
        
        # 3. 跳转北大法宝
        search_params = {}
        if keyword:
            search_params['keyword'] = keyword
        if case_type:
            search_params['case_type'] = case_type
        if year:
            search_params['year'] = year
        
        if not self.goto_pkulaw(search_params):
            print_error("跳转失败，流程中止")
            return False
        
        self.wait_random()
        
        # 4. 搜索（如果有参数）
        if keyword or case_type or year:
            if not self.search_cases(keyword, case_type, year, court):
                print_warning("搜索可能未成功，继续收集当前页面...")
        
        time.sleep(2)
        
        # 5. 收集URL
        self.collect_urls(max_pages)
        
        # 6. 下载内容
        if self.stats['urls_collected'] > 0:
            self.download_content()
        else:
            print_warning("未收集到URL，跳过下载")
        
        # 统计
        elapsed = time.time() - start_time
        print_header("流程完成统计")
        print_info(f"运行时间: {elapsed:.1f} 秒")
        print_info(f"收集URL: {self.stats['urls_collected']} 个")
        print_info(f"下载成功: {self.stats['urls_downloaded']} 个")
        print_info(f"下载目录: {self.folder_path}")
        print_info(f"URL文件: {self.urls_file}")
        
        return True

# ============== 主程序 ==============
def show_menu():
    """显示主菜单"""
    print_header("北大法宝图书馆自动爬虫 - 天津大学版")
    print(f"{Colors.CYAN}1.{Colors.ENDC} 启动全自动流程（登录→跳转→搜索→收集→下载）")
    print(f"{Colors.CYAN}2.{Colors.ENDC} 仅登录图书馆")
    print(f"{Colors.CYAN}3.{Colors.ENDC} 仅跳转到北大法宝")
    print(f"{Colors.CYAN}4.{Colors.ENDC} 仅搜索案件")
    print(f"{Colors.CYAN}5.{Colors.ENDC} 仅收集URL")
    print(f"{Colors.CYAN}6.{Colors.ENDC} 仅下载案件")
    print(f"{Colors.CYAN}0.{Colors.ENDC} 退出")
    print()

def main():
    """主函数"""
    # 检查Windows系统
    if sys.platform != 'win32':
        print_warning("此脚本针对Windows优化，其他系统可能需要调整")
    
    crawler = PkulawLibraryCrawler()
    
    while True:
        show_menu()
        choice = input_text("请选择操作", "1")
        
        if choice == '0':
            print_success("感谢使用，再见！")
            break
        
        elif choice == '1':
            # 全自动流程
            print_info("请配置搜索参数（直接回车使用默认值）：")
            keyword = input_text("搜索关键词", DEFAULT_KEYWORD)
            case_type = input_text("案件类型（如：民事案件/刑事案件）", DEFAULT_CASE_TYPE)
            year = input_text("年份（如：2024）", DEFAULT_YEAR)
            court = input_text("法院（如：最高人民法院）", DEFAULT_COURT)
            max_pages = int(input_text("最大翻页数", str(DEFAULT_MAX_PAGES)))
            
            print()
            confirm = input_yes_no("确认启动全自动流程？", True)
            if confirm:
                crawler.run_full_auto(keyword, case_type, year, court, max_pages)
            
        elif choice == '2':
            # 仅登录
            if crawler.init_browser():
                crawler.login_library()
        
        elif choice == '3':
            # 仅跳转
            if crawler.init_browser():
                crawler.goto_pkulaw()
        
        elif choice == '4':
            # 仅搜索
            keyword = input_text("搜索关键词")
            case_type = input_text("案件类型")
            year = input_text("年份")
            if crawler.pkulaw_page or crawler.init_browser():
                crawler.search_cases(keyword, case_type, year)
        
        elif choice == '5':
            # 仅收集
            max_pages = int(input_text("最大翻页数", "5"))
            if crawler.pkulaw_page or crawler.init_browser():
                crawler.collect_urls(max_pages)
        
        elif choice == '6':
            # 仅下载
            if crawler.pkulaw_page or crawler.init_browser():
                crawler.download_content()
        
        else:
            print_error("无效选择")
        
        print()
        input("按回车键继续...")
        os.system('cls' if os.name == 'nt' else 'clear')  # 清屏

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_warning("用户中断程序")
        sys.exit(0)
    except Exception as e:
        print_error(f"程序异常: {e}")
        sys.exit(1)
