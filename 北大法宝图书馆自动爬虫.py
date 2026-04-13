#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北大法宝图书馆自动爬虫 - 天津大学版（终端版）
全自动流程：登录图书馆 → 跳转北大法宝 → 搜索案件 → 批量下载

使用方法:
    python 北大法宝图书馆自动爬虫.py
"""

from DrissionPage import Chromium
import time
import random
import os
import sys
import re
import zipfile
import urllib.request
import urllib.parse

# ============== 配置 ==============
LIBRARY_URL = 'https://eds.tju.edu.cn/ermsClient/browse.do'
LIBRARY_ACCOUNT = '017656'
LIBRARY_PASSWORD = 'Lhy740220'
CHROME_PORT = '127.0.0.1:9333'

# ============== 终端颜色 ==============
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def print_step(step, text):
    print(f"{Colors.CYAN}[步骤 {step}]{Colors.ENDC} {Colors.BOLD}{text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {text}")

def print_success(text):
    print(f"{Colors.GREEN}[✓]{Colors.ENDC} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}[!]{Colors.ENDC} {text}")

def print_error(text):
    print(f"{Colors.RED}[✗]{Colors.ENDC} {text}")

# ============== 爬虫类 ==============
class PkulawCrawler:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.urls_file = os.path.join(base_dir, 'urls.txt')
        self.folder_path = os.path.join(base_dir, 'downloads')
        self.browser = None
        self.page = None
        self.pkulaw_page = None
        
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            print_info(f"创建下载目录: {self.folder_path}")
    
    def init_browser(self):
        """连接Chrome浏览器"""
        print_info("正在连接到Chrome浏览器...")
        try:
            self.browser = Chromium(CHROME_PORT)
            self.page = self.browser.latest_tab
            print_success(f"已连接到浏览器: {self.page.title}")
            return True
        except Exception as e:
            print_error(f"连接失败: {e}")
            print_info("请先启动Chrome调试模式: chrome.exe --remote-debugging-port=9333")
            return False
    
    def wait(self, min_sec=2, max_sec=5):
        """随机等待"""
        sec = random.randint(min_sec, max_sec)
        print_info(f"等待 {sec} 秒...")
        time.sleep(sec)
    
    def handle_login_popup(self):
        """处理登录弹窗"""
        try:
            # 检查"账户已在其他地方登录"弹窗
            popup_text = self.page.ele('text:您的账户已经在其他地方登录', timeout=2)
            if popup_text:
                print_info("检测到'账户已在其他地方登录'弹窗")
                time.sleep(1)
                
                # 在弹窗内找按钮 - 先找到弹窗容器
                dialog = None
                try:
                    dialog = self.page.ele('.el-dialog, .el-message-box', timeout=2)
                except:
                    pass
                
                # 找"登录"按钮（优先在弹窗内查找）
                continue_btn = None
                
                # 方法1: 在弹窗内查找
                if dialog:
                    try:
                        continue_btn = dialog.ele('text:登录', timeout=2)
                        print_info("在弹窗内找到登录按钮")
                    except:
                        pass
                
                # 方法2: 使用XPath精确定位弹窗按钮
                if not continue_btn:
                    try:
                        # 查找包含"其他地方登录"文本的弹窗内的登录按钮
                        continue_btn = self.page.ele('xpath://div[contains(text(),"其他地方登录") or contains(@class,"el-dialog")]//button//span[contains(text(),"登录")]/parent::button', timeout=2)
                        if not continue_btn:
                            continue_btn = self.page.ele('xpath://div[contains(@class,"el-dialog") or contains(@class,"el-message-box")]//button[contains(.//span,"登录")]', timeout=2)
                        if continue_btn:
                            print_info("使用XPath找到登录按钮")
                    except:
                        pass
                
                # 方法3: 查找所有登录按钮，取最后一个（通常弹窗的在后面）
                if not continue_btn:
                    try:
                        buttons = self.page.eles('text:登录')
                        if buttons and len(buttons) > 1:
                            continue_btn = buttons[-1]  # 取最后一个
                            print_info(f"使用最后一个登录按钮，共{len(buttons)}个")
                    except:
                        pass
                
                if not continue_btn:
                    print_error("未找到登录按钮")
                    return False
                
                # 点击按钮（先尝试正常点击，失败则用JS）
                try:
                    continue_btn.click()
                    print_info("已点击继续登录")
                except Exception as e:
                    print_info(f"点击失败，使用JS点击: {e}")
                    try:
                        continue_btn.run_js('this.click()')
                        print_info("已使用JS点击继续登录")
                    except Exception as e2:
                        print_error(f"JS点击也失败: {e2}")
                        return False
                
                time.sleep(3)
                return True
            return False
        except Exception as e:
            print_info(f"处理登录弹窗出错: {e}")
            return False
    
    def login_library(self):
        """登录图书馆"""
        print_step(1, "登录图书馆")
        
        try:
            print_info(f"访问: {LIBRARY_URL}")
            self.page.get(LIBRARY_URL)
            time.sleep(3)
            print_info(f"当前页面: {self.page.title}")
            
            # 检查是否已登录
            try:
                logout_btn = self.page.ele('text:退出', timeout=2)
                if logout_btn:
                    print_success("检测到已登录状态，跳过登录")
                    return True
            except:
                pass
            
            # 处理可能的弹窗
            self.handle_login_popup()
            
            # 再次检查是否已登录
            try:
                logout_btn = self.page.ele('text:退出', timeout=2)
                if logout_btn:
                    print_success("已登录")
                    return True
            except:
                pass
            
            # 查找登录按钮
            print_info("查找登录按钮...")
            login_btn = None
            try:
                login_btn = self.page.ele('text:登录', timeout=2)
            except:
                links = self.page.eles('tag:a')
                for link in links:
                    if '登录' in (link.text or ''):
                        login_btn = link
                        break
            
            if not login_btn:
                print_error("未找到登录按钮")
                return False
            
            # 点击登录
            print_info("点击登录按钮...")
            try:
                login_btn.click()
            except:
                login_btn.run_js('this.click()')
            
            time.sleep(3)
            print_info(f"点击后页面: {self.page.title}")
            
            # 填写账号密码
            print_info("填写登录信息...")
            
            # 学工号
            account_input = None
            for selector in ['css:input[type=text]', 'tag:input@name=username', 'tag:input@name=account']:
                try:
                    account_input = self.page.ele(selector, timeout=1)
                    if account_input:
                        break
                except:
                    continue
            
            if not account_input:
                print_error("未找到账号输入框")
                return False
            
            account_input.clear()
            account_input.input(LIBRARY_ACCOUNT)
            print_info(f"已填写学工号: {LIBRARY_ACCOUNT}")
            
            # 密码
            password_input = None
            try:
                password_input = self.page.ele('tag:input@type=password', timeout=2)
            except:
                pass
            
            if not password_input:
                print_error("未找到密码输入框")
                return False
            
            password_input.clear()
            password_input.input(LIBRARY_PASSWORD)
            print_info("已填写密码")
            
            # 提交登录
            print_info("提交登录...")
            try:
                submit_btn = self.page.ele('.login-btn', timeout=2)
                submit_btn.click()
            except:
                try:
                    self.page.run_js('document.querySelector(".login-btn").click()')
                except:
                    password_input.input('\n')
            
            time.sleep(5)
            print_info(f"等待后页面: {self.page.title}")
            
            # 处理可能的弹窗
            self.handle_login_popup()
            
            # 再次检查登录状态
            try:
                logout_btn = self.page.ele('text:退出', timeout=2)
                if logout_btn:
                    print_success("登录成功！检测到退出按钮")
                    return True
            except:
                pass
            
            # 检查是否还在登录页面
            if 'login' in self.page.url.lower() or '统一认证' in self.page.title:
                # 检查是否有错误提示
                try:
                    error_msg = self.page.ele('.error-msg', timeout=2)
                    if error_msg:
                        print_error(f"登录失败: {error_msg.text}")
                        return False
                except:
                    pass
                
                print_error("登录失败，仍在登录页面")
                return False
            
            print_success(f"登录成功！当前页面: {self.page.title}")
            return True
            
        except Exception as e:
            print_error(f"登录出错: {e}")
            return False
    
    def goto_pkulaw(self):
        """跳转到北大法宝"""
        print_step(2, "跳转北大法宝")
        
        try:
            print_info("查找北大法宝访问入口...")
            
            # 查找北大法宝链接
            pkulaw_link = None
            try:
                pkulaw_link = self.page.ele('text:北大法宝', timeout=3)
            except:
                pass
            
            if not pkulaw_link:
                links = self.page.eles('tag:a')
                for link in links:
                    text = link.text or ''
                    if '北大法宝' in text:
                        pkulaw_link = link
                        break
            
            if pkulaw_link:
                link_href = pkulaw_link.attr('href') or ''
                print_info(f"找到北大法宝入口: {link_href[:60]}")
                
                # 情况1：直接是entry.do链接
                if 'entry.do' in link_href:
                    print_info("直接访问entry.do...")
                    if link_href.startswith('http'):
                        self.page.get(link_href)
                    else:
                        self.page.get(f"https://eds.tju.edu.cn{link_href}")
                    time.sleep(10)
                    
                # 情况2：是资源详情页链接，需要先访问详情页
                elif 'eresourceInfo.do' in link_href or 'rid=' in link_href:
                    print_info("先访问资源详情页...")
                    # 直接访问详情页URL
                    if link_href.startswith('http'):
                        detail_url = link_href
                    else:
                        detail_url = f"https://eds.tju.edu.cn{link_href}"
                    
                    print_info(f"访问: {detail_url}")
                    self.page.get(detail_url)
                    time.sleep(5)
                    
                    # 在详情页查找entry.do链接
                    print_info("查找entry.do访问入口...")
                    time.sleep(2)
                    
                    entry_url = None
                    # 方法1：找所有链接
                    try:
                        links = self.page.eles('tag:a')
                        print_info(f"详情页有 {len(links)} 个链接")
                        for link in links:
                            href = link.attr('href') or ''
                            text = link.text or ''
                            if 'entry.do' in href:
                                entry_url = href if href.startswith('http') else f"https://eds.tju.edu.cn{href}"
                                print_info(f"找到entry链接: {text[:30]} -> {entry_url[:60]}")
                                break
                    except Exception as e:
                        print_info(f"查找链接出错: {e}")
                    
                    if entry_url:
                        print_info(f"访问: {entry_url}")
                        self.page.get(entry_url)
                        time.sleep(10)
                    else:
                        print_error("无法找到或构造entry.do链接")
                        return False
                else:
                    # 其他情况，直接点击
                    print_info("点击链接...")
                    try:
                        pkulaw_link.click()
                    except:
                        pkulaw_link.run_js('this.click()')
                    time.sleep(8)
            else:
                print_info("未找到链接，尝试直接访问北大法宝...")
                self.page.get('https://www.pkulaw.com/')
                time.sleep(5)
            
            # 获取北大法宝标签页
            tabs = self.browser.get_tabs()
            for tab in tabs:
                try:
                    if 'pkulaw' in tab.url.lower() or '.eds.tju.edu.cn' in tab.url.lower():
                        self.pkulaw_page = tab
                        break
                except:
                    continue
            
            if not self.pkulaw_page:
                self.pkulaw_page = self.browser.latest_tab
            
            page_url = self.pkulaw_page.url.lower()
            print_info(f"当前页面: {self.pkulaw_page.title} - {page_url}")
            
            if 'pkulaw' in page_url or '.eds.tju.edu.cn' in page_url:
                print_success(f"已进入北大法宝: {self.pkulaw_page.title}")
                return True
            else:
                print_error(f"未进入北大法宝: {page_url}")
                return False
            
        except Exception as e:
            print_error(f"跳转出错: {e}")
            return False
    
    def select_database(self, db_type='法律法规'):
        """选择数据库类型"""
        print_info(f"选择数据库: {db_type}")
        
        try:
            page = self.pkulaw_page
            current_url = page.url
            
            # 从当前URL中提取基础代理地址
            match = re.match(r'(https?://[^/]+)', current_url)
            if not match:
                print_error("无法解析当前URL")
                return False
            
            base_url = match.group(1)
            
            # 数据库类型对应的路径
            db_paths = {
                '法律法规': '/law?way=topGuid',
                '司法案例': '/case?way=topGuid',
            }
            
            if db_type in db_paths:
                target_url = base_url + db_paths[db_type]
                print_info(f"访问 {db_type} 数据库: {target_url}")
                page.get(target_url)
                time.sleep(5)
                print_info(f"当前页面: {page.title}")
                return True
            else:
                print_warning(f"未知的数据库类型: {db_type}")
                return True
                
        except Exception as e:
            print_error(f"选择数据库出错: {e}")
            return False
    
    def search_cases(self, keyword='', db_type='法律法规'):
        """搜索案件"""
        print_step(3, f"搜索案件 - {db_type}")
        
        try:
            page = self.pkulaw_page
            
            # 先选择数据库类型
            if not self.select_database(db_type):
                return False
            
            if not keyword:
                print_info("无搜索关键词")
                return True
            
            print_info(f"搜索关键词: {keyword}")
            
            # 查找搜索框
            search_input = None
            for selector in ['css:input[type=text]', 'tag:input@id=keyword', 'tag:input@name=keyword']:
                try:
                    search_input = page.ele(selector, timeout=2)
                    if search_input:
                        break
                except:
                    continue
            
            if search_input:
                search_input.clear()
                search_input.input(keyword)
                print_info(f"已输入关键词: {keyword}")
                time.sleep(1)
                
                # 按回车搜索
                search_input.input('\n')
                print_info("已按回车搜索")
                time.sleep(5)
                print_info(f"搜索后页面: {page.title}")
            else:
                print_warning("未找到搜索框")
            
            return True
            
        except Exception as e:
            print_error(f"搜索出错: {e}")
            return False
    
    def click_no_group(self):
        """点击'不分组'选项"""
        print_info("点击'不分组'选项...")
        try:
            no_group_btn = self.pkulaw_page.ele('text:不分组', timeout=3)
            try:
                no_group_btn.click()
            except:
                print_info("直接点击失败，使用JS点击...")
                no_group_btn.run_js('this.click()')
            print_info("已点击'不分组'，等待页面刷新...")
            time.sleep(3)
            return True
        except Exception as e:
            print_info(f"点击'不分组'失败: {e}")
            return False
    
    def get_total_pages(self):
        """获取总页数"""
        try:
            page = self.pkulaw_page
            
            # 尝试从分页信息获取总页数
            # 格式如：页数 1/100
            try:
                page_info = page.ele('text:/\\d+/\\d+', timeout=2)
                if page_info:
                    text = page_info.text
                    match = re.search(r'(\d+)/(\d+)', text)
                    if match:
                        current_page = int(match.group(1))
                        total_pages = int(match.group(2))
                        print_info(f"分页信息: 第{current_page}页/共{total_pages}页")
                        return total_pages
            except:
                pass
            
            # 备用方法：找总页数文本
            try:
                total_text = page.ele('text:共.*篇', timeout=2)
                if total_text:
                    text = total_text.text
                    match = re.search(r'共(\d+)', text)
                    if match:
                        total_count = int(match.group(1))
                        # 假设每页20条
                        total_pages = (total_count + 19) // 20
                        print_info(f"总数量: {total_count}篇，估算总页数: {total_pages}页")
                        return total_pages
            except:
                pass
            
            print_warning("无法获取总页数，使用默认值100")
            return 100
            
        except Exception as e:
            print_error(f"获取总页数出错: {e}")
            return 100
    
    def download_and_extract_zip(self, zip_url, page_num):
        """下载zip并解压"""
        try:
            # 下载zip文件
            zip_filename = os.path.join(self.folder_path, f'page_{page_num}.zip')
            print_info(f"下载ZIP文件: {zip_url[:80]}...")
            
            # 设置请求头模拟浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
            }
            req = urllib.request.Request(zip_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(zip_filename, 'wb') as f:
                    f.write(response.read())
            
            print_info(f"ZIP文件已下载: {zip_filename}")
            
            # 解压zip文件
            print_info("解压ZIP文件...")
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(self.folder_path)
            
            print_info(f"已解压到: {self.folder_path}")
            
            # 删除zip文件
            os.remove(zip_filename)
            print_info(f"已删除ZIP文件")
            
            return True
            
        except Exception as e:
            print_error(f"下载或解压ZIP失败: {e}")
            return False
    
    def download_page(self, page_num):
        """下载当前页的所有数据"""
        try:
            page = self.pkulaw_page
            print_info(f"开始下载第 {page_num} 页...")
            
            # 1. 点击"全选"
            print_info("点击'全选'...")
            try:
                # 等待页面加载完成（检查列表是否存在）
                time.sleep(3)
                try:
                    page.ele('.result-list, .list-item, [class*=result], tr', timeout=5)
                    print_info("页面列表已加载")
                except:
                    print_warning("等待列表加载...")
                    time.sleep(5)
                
                select_all_btn = page.ele('text:全选', timeout=3)
                
                # 先取消全选（如果有的话），再重新全选
                try:
                    select_all_btn.click()
                except:
                    select_all_btn.run_js('this.click()')
                print_info("已点击'全选'")
                time.sleep(3)
                
                # 验证是否选中（检查复选框状态）
                checked_count = 0
                try:
                    checked_boxes = page.eles('css:input[type=checkbox]:checked')
                    checked_count = len(checked_boxes)
                    print_info(f"已选中 {checked_count} 项")
                except:
                    pass
                
                # 如果选中项太少（1-3项），可能是全选没生效，重试
                if checked_count <= 3:
                    print_warning(f"选中项目较少({checked_count}项)，等待后重试全选...")
                    time.sleep(3)
                    try:
                        # 重新点击全选按钮
                        select_all_btn = page.ele('text:全选', timeout=3)
                        try:
                            select_all_btn.click()
                        except:
                            select_all_btn.run_js('this.click()')
                        time.sleep(3)
                        checked_boxes = page.eles('css:input[type=checkbox]:checked')
                        checked_count = len(checked_boxes)
                        print_info(f"重试后选中 {checked_count} 项")
                    except Exception as retry_e:
                        print_info(f"重试失败: {retry_e}")
                
                # 如果还是没选中，可能是当前页确实没有数据，跳过
                if checked_count == 0:
                    print_warning("当前页未选中任何项目，跳过...")
                    return False
                    
            except Exception as e:
                print_error(f"点击'全选'失败: {e}")
                return False
            
            # 2. 点击下载图标
            print_info("点击下载图标...")
            try:
                download_btn = None
                for selector in ['.download-btn', 'text:下载', '[title*=下载]', '[class*=download]', '.icon-download']:
                    try:
                        download_btn = page.ele(selector, timeout=2)
                        if download_btn:
                            break
                    except:
                        continue
                
                if download_btn:
                    try:
                        download_btn.click()
                    except:
                        download_btn.run_js('this.click()')
                    print_info("已点击下载按钮")
                    time.sleep(3)
                else:
                    print_error("未找到下载按钮")
                    return False
            except Exception as e:
                print_error(f"点击下载按钮失败: {e}")
                return False
            
            # 3. 在弹窗中选择"全文的纯文本"
            print_info("选择下载格式：全文的纯文本...")
            try:
                time.sleep(3)  # 等待弹窗完全打开
                
                # 检查弹窗是否打开
                dialog = None
                try:
                    dialog = page.ele('.el-dialog', timeout=3)
                    print_info("下载弹窗已打开")
                except:
                    print_warning("未检测到下载弹窗，继续尝试...")
                
                # 选择"全文" - 带重试
                for attempt in range(2):
                    try:
                        fulltext_option = page.ele('text:全文', timeout=3)
                        fulltext_option.click()
                        print_info("已选择'全文'")
                        time.sleep(1)
                        break
                    except Exception as e:
                        if attempt == 0:
                            print_warning(f"选择'全文'失败，重试...")
                            time.sleep(2)
                        else:
                            print_warning(f"选择'全文'失败: {e}")
                
                # 选择"纯文本" - 带重试
                for attempt in range(2):
                    try:
                        text_option = page.ele('text:纯文本', timeout=3)
                        text_option.click()
                        print_info("已选择'纯文本'")
                        time.sleep(1)
                        break
                    except Exception as e:
                        if attempt == 0:
                            print_warning(f"选择'纯文本'失败，重试...")
                            time.sleep(2)
                        else:
                            print_warning(f"选择'纯文本'失败: {e}")
                
            except Exception as e:
                print_error(f"选择下载格式失败: {e}")
                return False
            
            # 4. 点击确定，触发下载
            print_info("点击弹窗中的确定...")
            try:
                # 记录点击前的URL
                url_before = page.url
                print_info(f"点击前URL: {url_before}")
                
                # 等待确保弹窗完全打开
                time.sleep(2)
                
                # ========== DEBUG: 输出所有确定按钮信息 ==========
                print_info("========== DEBUG: 查找确定按钮 ==========")
                try:
                    all_buttons = page.eles('text:确定')
                    print_info(f"页面上共有 {len(all_buttons)} 个'确定'文本的元素")
                    
                    for i, btn in enumerate(all_buttons):
                        try:
                            tag = btn.tag or 'unknown'
                            class_attr = btn.attr('class') or '无class'
                            id_attr = btn.attr('id') or '无id'
                            text = btn.text or '无文本'
                            
                            # 获取父元素信息
                            parent = btn.parent()
                            parent_tag = parent.tag if parent else '无父元素'
                            parent_class = (parent.attr('class') or '无class') if parent else '无class'
                            
                            print(f"  [{i}] 标签:{tag}, 类:{class_attr[:40]}, 父标签:{parent_tag}, 父类:{parent_class[:40]}, 文本:{text[:20]}")
                        except Exception as e:
                            print(f"  [{i}] 获取信息失败: {e}")
                except Exception as e:
                    print_info(f"获取按钮列表失败: {e}")
                
                # 尝试获取弹窗HTML
                print_info("DEBUG: 尝试获取弹窗HTML...")
                try:
                    dialog = page.ele('.el-dialog', timeout=2)
                    if dialog:
                        dialog_html = dialog.html[:500]
                        print_info(f"弹窗HTML片段: {dialog_html}")
                except Exception as e:
                    print_info(f"获取弹窗HTML失败: {e}")
                print_info("========== DEBUG END ==========")
                # ========== DEBUG END ==========
                
                # 在弹窗中查找确定按钮
                confirm_btn = None
                
                # 方法1: 优先查找class="submit"的确定按钮（弹窗中的确定按钮）
                try:
                    confirm_btn = page.ele('css:a.submit', timeout=3)
                    if confirm_btn and '确定' in (confirm_btn.text or ''):
                        print_info("找到class='submit'的确定按钮")
                except:
                    pass
                
                # 方法2: 查找弹窗容器，然后在其中找确定按钮
                if not confirm_btn:
                    try:
                        dialog = page.ele('.el-dialog', timeout=3)
                        if dialog:
                            # 在弹窗footer中找确定按钮
                            try:
                                footer = dialog.ele('.el-dialog__footer', timeout=2)
                                confirm_btn = footer.ele('text:确定', timeout=2)
                                print_info("在弹窗footer中找到确定按钮")
                            except:
                                # 直接在弹窗中找
                                confirm_btn = dialog.ele('text:确定', timeout=2)
                                print_info("在弹窗中找到确定按钮")
                    except:
                        pass
                
                # 方法3: 用XPath查找弹窗footer中的确定按钮
                if not confirm_btn:
                    try:
                        confirm_btn = page.ele('xpath://div[contains(@class,"el-dialog__footer")]//button[contains(.//span,"确定")]', timeout=3)
                        if confirm_btn:
                            print_info("使用XPath找到确定按钮")
                    except Exception as e:
                        print_info(f"XPath查找失败")
                
                # 方法4: 直接找所有确定按钮，取最后一个（备用方案）
                if not confirm_btn:
                    try:
                        buttons = page.eles('text:确定')
                        if buttons:
                            confirm_btn = buttons[-1]  # 取最后一个
                            print_info(f"使用最后一个确定按钮，共{len(buttons)}个")
                    except:
                        pass
                
                if not confirm_btn:
                    print_error("未找到确定按钮")
                    return False
                
                # 点击确定
                click_success = False
                try:
                    confirm_btn.click()
                    print_info("已点击确定")
                    click_success = True
                except Exception as e:
                    print_info(f"点击失败: {e}，使用JS点击...")
                    try:
                        confirm_btn.run_js('this.click()')
                        print_info("已使用JS点击确定")
                        click_success = True
                    except Exception as e2:
                        print_error(f"JS点击也失败: {e2}")
                
                time.sleep(5)
                
                # 检查是否有新标签页打开
                tabs = self.browser.get_tabs()
                new_tab = None
                for tab in tabs:
                    if tab != self.pkulaw_page and tab.url != url_before:
                        new_tab = tab
                        break
                
                if new_tab:
                    download_url = new_tab.url
                    print_info(f"新标签页URL: {download_url}")
                    
                    if '.zip' in download_url.lower():
                        print_info("检测到ZIP下载链接")
                        # 切换到新标签页下载
                        self.pkulaw_page = new_tab
                        if self.download_and_extract_zip(download_url, page_num):
                            print_success(f"第 {page_num} 页下载并解压完成")
                            # 关闭下载标签页，回到原页面
                            try:
                                self.browser.get_tabs()[0].set.active()
                            except:
                                self.browser.get_tabs()[0]()
                            self.pkulaw_page = self.browser.get_tabs()[0]
                            # 关闭原页面的弹窗
                            self.close_download_dialog()
                            return True
                        return False
                    else:
                        print_info(f"新页面: {download_url}")
                        print_success(f"第 {page_num} 页下载已触发")
                        # 切换回主标签页关闭弹窗
                        for tab in self.browser.get_tabs():
                            if 'law' in tab.url or 'case' in tab.url:
                                try:
                                    tab.set.active()
                                except:
                                    tab()
                                self.pkulaw_page = tab
                                break
                        self.close_download_dialog()
                        return True
                else:
                    # 检查当前URL是否变化
                    url_after = page.url
                    print_info(f"点击后URL: {url_after}")
                    
                    if url_after != url_before:
                        if '.zip' in url_after.lower():
                            print_info("页面变为ZIP下载")
                            if self.download_and_extract_zip(url_after, page_num):
                                print_success(f"第 {page_num} 页下载完成")
                                return True
                            return False
                        else:
                            print_success(f"第 {page_num} 页下载已触发")
                            # 关闭弹窗
                            self.close_download_dialog()
                            return True
                    else:
                        print_warning("URL未变化，下载可能通过浏览器自动处理")
                        print_success(f"第 {page_num} 页下载任务已提交")
                        # 关闭弹窗
                        self.close_download_dialog()
                        return True
                    
            except Exception as e:
                print_error(f"点击确定失败: {e}")
                return False
            
        except Exception as e:
            print_error(f"下载第 {page_num} 页出错: {e}")
            return False
    
    def close_download_dialog(self):
        """关闭下载弹窗（点击右上角×）"""
        try:
            print_info("关闭下载弹窗...")
            # 尝试多种关闭按钮选择器
            close_btn = None
            for selector in ['.el-dialog__close', '.close-btn', 'text:×', 'text:关闭', '[class*=close]', '.icon-close']:
                try:
                    close_btn = self.pkulaw_page.ele(selector, timeout=2)
                    if close_btn:
                        print_info(f"找到关闭按钮: {selector}")
                        break
                except:
                    continue
            
            if close_btn:
                try:
                    close_btn.click()
                except:
                    close_btn.run_js('this.click()')
                print_info("已关闭弹窗")
                time.sleep(1)
            else:
                # 尝试按ESC键关闭
                try:
                    self.pkulaw_page.run_js('document.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape"}))')
                    print_info("已按ESC关闭弹窗")
                    time.sleep(1)
                except:
                    print_warning("未找到关闭按钮")
        except Exception as e:
            print_info(f"关闭弹窗出错: {e}")
    
    def go_to_next_page(self):
        """点击下一页"""
        try:
            page = self.pkulaw_page
            print_info("点击下一页...")
            
            # 查找下一页按钮
            next_btn = None
            for selector in ['text:下一页', '.next', '[title*=下一页]', '[class*=next]']:
                try:
                    next_btn = page.ele(selector, timeout=2)
                    if next_btn:
                        btn_class = next_btn.attr('class') or ''
                        if 'disabled' not in btn_class:
                            break
                        else:
                            next_btn = None
                except:
                    continue
            
            if next_btn:
                try:
                    next_btn.click()
                except:
                    next_btn.run_js('this.click()')
                print_info("已点击下一页，等待页面加载...")
                time.sleep(8)  # 增加等待时间，确保页面完全加载
                
                # 检查页面是否加载完成（通过检查全选按钮和列表是否存在）
                try:
                    page.ele('text:全选', timeout=5)
                    # 额外检查列表是否加载
                    page.ele('.result-list, .list-item, [class*=result], tr', timeout=5)
                    print_info("新页面已加载，找到全选按钮和列表")
                except:
                    print_warning("新页面可能未完全加载，继续等待...")
                    time.sleep(5)
                
                return True
            else:
                print_info("无下一页按钮")
                return False
                
        except Exception as e:
            print_error(f"点击下一页出错: {e}")
            return False
    
    def batch_download(self, max_pages=5):
        """批量下载"""
        print_step(4, f"批量下载（最多{max_pages}页）")
        
        try:
            # 1. 点击不分组
            if not self.click_no_group():
                print_warning("点击'不分组'失败，继续尝试下载...")
            
            # 2. 获取总页数
            total_pages = self.get_total_pages()
            
            # 3. 确定要下载的页数
            pages_to_download = min(max_pages, total_pages)
            print_info(f"计划下载: {pages_to_download} 页 (用户设置{max_pages}页, 实际共{total_pages}页)")
            
            # 4. 逐页下载
            success_count = 0
            for page_num in range(1, pages_to_download + 1):
                print_info(f"\n处理第 {page_num}/{pages_to_download} 页...")
                
                # 下载当前页
                if self.download_page(page_num):
                    success_count += 1
                
                # 如果不是最后一页，点击下一页
                if page_num < pages_to_download:
                    if not self.go_to_next_page():
                        print_warning("无法翻到下一页，结束下载")
                        break
            
            print_success(f"批量下载完成: 成功提交 {success_count}/{pages_to_download} 页下载任务")
            print_info(f"文件将下载到浏览器默认下载目录")
            return success_count
            
        except Exception as e:
            print_error(f"批量下载出错: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def run(self, keyword='', max_pages=5, db_type='法律法规'):
        """运行完整流程"""
        print_header("北大法宝图书馆自动爬虫启动")
        
        start = time.time()
        
        # 1. 连接浏览器
        if not self.init_browser():
            return False
        
        # 2. 登录图书馆
        if not self.login_library():
            print_error("登录失败，程序中止")
            return False
        
        self.wait()
        
        # 3. 跳转北大法宝
        if not self.goto_pkulaw():
            print_error("跳转失败，程序中止")
            return False
        
        self.wait()
        
        # 4. 搜索案件
        if not self.search_cases(keyword, db_type):
            print_error("搜索失败")
            return False
        
        # 5. 批量下载
        downloaded_pages = self.batch_download(max_pages)
        
        # 统计
        elapsed = time.time() - start
        print_header("运行统计")
        print_info(f"运行时间: {elapsed:.1f} 秒")
        print_info(f"数据库类型: {db_type}")
        print_info(f"搜索关键词: {keyword if keyword else '无'}")
        print_info(f"成功提交下载: {downloaded_pages} 页")
        print_info(f"文件下载位置: 浏览器默认下载目录")
        
        return True

# ============== 主程序 ==============
def main():
    print_header("北大法宝图书馆自动爬虫 - 天津大学版")
    
    print("使用说明:")
    print("1. 先启动Chrome调试模式: chrome.exe --remote-debugging-port=9333")
    print("2. 按提示输入搜索参数")
    print()
    
    # 输入参数
    print("数据库类型:")
    print("  1. 法律法规 (默认)")
    print("  2. 司法案例")
    db_choice = input("请选择数据库类型 (1/2，默认1): ").strip()
    db_type = '司法案例' if db_choice == '2' else '法律法规'
    
    keyword = input("搜索关键词（直接回车表示不搜索）: ").strip()
    max_pages = input("最大下载页数（默认5）: ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 5
    
    print()
    print("=" * 50)
    print(f"数据库类型: {db_type}")
    print(f"搜索关键词: {keyword if keyword else '无'}")
    print(f"最大下载页数: {max_pages}")
    print("=" * 50)
    
    confirm = input("\n确认开始？(Y/n): ").strip().lower()
    if confirm and confirm not in ['y', 'yes', '是']:
        print("已取消")
        return
    
    # 运行
    crawler = PkulawCrawler()
    crawler.run(keyword=keyword, max_pages=max_pages, db_type=db_type)
    
    print()
    input("按回车键退出...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中止")
    except Exception as e:
        print_error(f"程序错误: {e}")
