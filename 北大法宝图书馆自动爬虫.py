#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北大法宝图书馆自动爬虫 - 天津大学版（终端版）
全自动流程：登录图书馆 → 跳转北大法宝 → 搜索案件 → 下载内容

使用方法:
    python 北大法宝图书馆自动爬虫.py
"""

from DrissionPage import Chromium
import time
import random
import os
import sys

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

def print_progress(current, total, text=""):
    percent = int((current / total) * 100) if total > 0 else 0
    bar = '█' * int(40 * percent / 100) + '░' * (40 - int(40 * percent / 100))
    print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} {percent}% ({current}/{total}) {text}", end='', flush=True)
    if current == total:
        print()

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
    
    def check_login_status(self):
        """检查是否已登录"""
        try:
            # 检查页面上是否有退出/个人中心等已登录标志
            logout_ele = self.page.ele('text:退出', timeout=2)
            if logout_ele:
                return True
            
            # 检查是否有用户名显示
            user_ele = self.page.ele('.user-name', timeout=1)
            if user_ele and user_ele.text:
                return True
            
            # 检查是否有个人中心
            profile_ele = self.page.ele('text:个人中心', timeout=1)
            if profile_ele:
                return True
            
            # 检查页面上是否有"登录"按钮 - 如果有，说明未登录
            try:
                login_btn = self.page.ele('text:登录', timeout=1)
                if login_btn:
                    return False  # 有登录按钮，说明未登录
            except:
                pass
            
            # 如果既不是电子资源平台首页，也不是登录页面，可能是已登录的其他页面
            if 'login' not in self.page.url.lower() and '统一认证' not in self.page.title:
                return True
                
            return False
        except:
            return False
    
    def handle_popup(self):
        """处理可能的弹窗"""
        try:
            # 检查"账户已在其他地方登录"弹窗
            popup_text = self.page.ele('text:您的账户已经在其他地方登录', timeout=2)
            if popup_text:
                print_info("检测到'账户已在其他地方登录'弹窗")
                # 找"登录"或"继续登录"按钮
                try:
                    continue_btn = self.page.ele('text:登录', timeout=2)
                    continue_btn.click()
                    print_info("已点击继续登录")
                    time.sleep(3)
                    return True
                except:
                    try:
                        continue_btn = self.page.ele('text:继续', timeout=1)
                        continue_btn.click()
                        print_info("已点击继续")
                        time.sleep(3)
                        return True
                    except:
                        pass
            
            # 检查其他可能的弹窗
            try:
                close_btn = self.page.ele('.el-dialog__close', timeout=1)
                if close_btn:
                    close_btn.click()
                    print_info("已关闭弹窗")
                    time.sleep(1)
            except:
                pass
                
            return False
        except:
            return False
    
    def login_library(self):
        """登录图书馆 - 点击右上角登录按钮"""
        print_step(1, "登录图书馆")
        
        try:
            # 访问图书馆网站
            print_info(f"访问: {LIBRARY_URL}")
            self.page.get(LIBRARY_URL)
            time.sleep(3)
            print_info(f"当前页面: {self.page.title}")
            
            # 检查是否已登录（看是否有退出按钮等）
            if self.check_login_status():
                print_success("检测到已登录状态（有退出/个人中心等），跳过登录")
                return True
            
            # 处理可能的弹窗
            self.handle_popup()
            
            # 再次检查
            if self.check_login_status():
                print_success("已登录，跳过")
                return True
            
            # 检查页面上是否有登录按钮
            print_info("检查页面状态...")
            has_login_btn = False
            try:
                login_check = self.page.ele('text:登录', timeout=2)
                if login_check:
                    has_login_btn = True
            except:
                pass
            
            # 如果页面上没有登录按钮，可能已经登录
            if not has_login_btn:
                print_success("页面上没有登录按钮，判断为已登录状态")
                return True
            
            # 点击右上角的"登录"按钮
            print_info("查找登录按钮...")
            
            login_btn = None
            login_url = None
            # 尝试多种方式找到登录按钮
            selectors = [
                'text:登录',           # 通过文本
                '.login',              # class名
                '#login',              # id
                '[href*="login"]',     # 包含login的链接
                'tag:a@title=登录',    # title属性
            ]
            
            for selector in selectors:
                try:
                    login_btn = self.page.ele(selector, timeout=2)
                    if login_btn:
                        href = login_btn.attr('href')
                        if href:
                            login_url = href if href.startswith('http') else f"https://eds.tju.edu.cn{href}"
                        print_info(f"找到登录按钮: {selector}, URL={login_url}")
                        break
                except:
                    continue
            
            if not login_btn:
                # 如果找不到，尝试获取所有链接查看
                links = self.page.eles('tag:a')
                for link in links:
                    text = link.text or ''
                    href = link.attr('href') or ''
                    if '登录' in text and len(text) < 5:  # 短文本"登录"
                        login_btn = link
                        login_url = href if href.startswith('http') else f"https://eds.tju.edu.cn{href}"
                        print_info(f"通过遍历找到登录按钮: {text}, URL={login_url}")
                        break
            
            if not login_btn and not login_url:
                print_warning("未找到登录按钮，尝试直接访问登录URL...")
                login_url = "https://eds.tju.edu.cn/ermsClient/viewLogin.do"
            
            # 记录点击前页面
            page_before_click = self.page.title
            
            # 点击登录按钮或访问登录URL
            if login_btn:
                print_info("点击登录按钮...")
                try:
                    # 方法1: 直接点击
                    login_btn.click()
                except Exception as e:
                    print_info(f"直接点击失败: {e}")
                    # 方法2: JavaScript点击
                    try:
                        login_btn.run_js('this.click()')
                        print_info("使用JavaScript点击")
                    except Exception as e2:
                        print_info(f"JavaScript点击也失败: {e2}")
                        # 方法3: 直接访问登录URL
                        if login_url:
                            print_info(f"直接访问登录URL: {login_url}")
                            self.page.get(login_url)
                        else:
                            print_error("无法点击也无法访问URL")
                            return False
            elif login_url:
                print_info(f"直接访问登录URL: {login_url}")
                self.page.get(login_url)
            else:
                print_error("没有登录按钮也没有登录URL")
                return False
            
            time.sleep(5)  # Vue单页应用跳转需要更长时间
            page_after_click = self.page.title
            print_info(f"点击后页面: {page_after_click}")
            
            # 如果页面没有变化（还是电子资源平台），说明已经是登录状态
            if page_before_click == page_after_click and '电子资源' in page_after_click:
                print_success("页面未变化，已是登录状态，跳过登录流程")
                return True
            
            # 检查是否跳转到统一认证页面
            if '统一认证' in self.page.title or '认证' in self.page.title:
                print_info("已进入统一认证登录页面")
                # Vue单页应用需要等待组件渲染
                print_info("等待Vue组件渲染...")
                time.sleep(3)
            
            # 检查是否有隐藏字段（如csrf token）
            print_info("检查隐藏字段...")
            try:
                hidden_inputs = self.page.eles('tag:input@type=hidden')
                print_info(f"发现 {len(hidden_inputs)} 个隐藏字段")
                for inp in hidden_inputs:
                    name = inp.attr('name') or '无名'
                    value = inp.attr('value') or ''
                    print(f"  {name}={value[:30] if value else '(空)'}")
            except:
                pass
            
            # 填写账号密码
            print_info("填写登录信息...")
            
            # 学工号/账号输入框（天津大学图书馆Vue单页应用）
            account_input = None
            selectors = [
                'tag:input@name=username',      # 最常见的用户名input
                'tag:input@name=account',       
                'tag:input@name=id',
                'tag:input@name=workNo',
                'tag:input@name=userId',
                'tag:input@id=username',
                'tag:input@id=account',
                'tag:input@id=id',
                'tag:input@placeholder*=学工号',  # placeholder包含学工号
                'tag:input@placeholder*=账号',
                'tag:input@placeholder*=用户名',
                'css:input[type=text]',         # Vue单页应用常用
                'css:input:not([type])',        # 无type默认text
            ]
            
            for selector in selectors:
                try:
                    account_input = self.page.ele(selector, timeout=1)
                    if account_input:
                        print_info(f"找到学工号输入框: {selector}")
                        break
                except:
                    continue
            
            # 如果没找到，尝试遍历所有input
            if not account_input:
                print_info("尝试遍历查找输入框...")
                inputs = self.page.eles('tag:input')
                for i, inp in enumerate(inputs):
                    input_type = inp.attr('type') or 'text'
                    placeholder = inp.attr('placeholder') or ''
                    if input_type in ['text', '']:
                        account_input = inp
                        print_info(f"找到学工号输入框: 第{i}个input, type={input_type}, placeholder={placeholder}")
                        break
            
            if not account_input:
                print_error("未找到学工号输入框")
                # 打印所有input元素供调试
                print_info("当前页面所有input元素:")
                try:
                    inputs = self.page.eles('tag:input')
                    for i, inp in enumerate(inputs):
                        name = inp.attr('name') or '无name'
                        id_attr = inp.attr('id') or '无id'
                        inp_type = inp.attr('type') or 'text'
                        placeholder = inp.attr('placeholder') or '无placeholder'
                        print(f"  [{i}] name={name}, id={id_attr}, type={inp_type}, placeholder={placeholder}")
                except Exception as e:
                    print_error(f"获取input列表失败: {e}")
                
                self.save_debug_html("login_form")
                return False
            
            account_input.clear()
            account_input.input(LIBRARY_ACCOUNT)
            print_info(f"已填写学工号: {LIBRARY_ACCOUNT}")
            
            # 密码输入框
            password_input = None
            password_selectors = [
                'tag:input@name=password',
                'tag:input@type=password',
                'tag:input@id=password',
                'tag:input@id=pwd',
                'tag:input@name=pwd',
                'tag:input@placeholder*=密码',
            ]
            
            for selector in password_selectors:
                try:
                    password_input = self.page.ele(selector, timeout=1)
                    if password_input:
                        print_info(f"找到密码输入框: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                print_error("未找到密码输入框")
                return False
            
            password_input.clear()
            password_input.input(LIBRARY_PASSWORD)
            print_info("已填写密码")
            
            # 提交登录
            print_info("提交登录...")
            submit_clicked = False
            
            # 方法1: 查找表单并提交
            try:
                form = self.page.ele('tag:form', timeout=2)
                if form:
                    print_info("找到表单，使用表单提交")
                    form.submit()
                    submit_clicked = True
            except Exception as e:
                print_info(f"表单提交失败: {e}")
            
            # 方法2: 点击登录按钮
            if not submit_clicked:
                print_info("尝试点击登录按钮...")
                
                # 先打印所有按钮供调试
                print_info("当前页面所有按钮:")
                try:
                    buttons = self.page.eles('tag:button')
                    for i, btn in enumerate(buttons):
                        btn_text = btn.text or btn.attr('value') or '无文本'
                        btn_class = btn.attr('class') or '无class'
                        btn_type = btn.attr('type') or '无type'
                        print(f"  [{i}] text={btn_text[:20]}, class={btn_class}, type={btn_type}")
                except Exception as e:
                    print_error(f"获取按钮列表失败: {e}")
                
                # 尝试多种方式点击登录按钮（Vue单页应用按钮是type=button）
                submit_selectors = [
                    '.login-btn',                   # Vue登录页面常用
                    'css:button.login-btn',
                    'tag:button@type=submit',
                    'tag:input@type=submit',
                    'text:登录',
                    '.btn-login',
                    '#login-btn',
                    '#submit',
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_btn = self.page.ele(selector, timeout=1)
                        btn_text = submit_btn.text or submit_btn.attr('value') or ''
                        print_info(f"点击登录按钮: {selector}, text='{btn_text}'")
                        submit_btn.click()
                        submit_clicked = True
                        
                        if submit_clicked:
                            break
                    except:
                        continue
                
                # 如果没找到，遍历按钮找登录
                if not submit_clicked:
                    try:
                        buttons = self.page.eles('tag:button')
                        for btn in buttons:
                            btn_text = btn.text or btn.attr('value') or ''
                            btn_class = btn.attr('class') or ''
                            if '登录' in btn_text or 'login' in btn_class.lower():
                                print_info(f"点击登录按钮: text='{btn_text}', class={btn_class}")
                                btn.click()
                                submit_clicked = True
                                break
                    except:
                        pass
            
            # 方法3: JavaScript点击
            if not submit_clicked:
                print_info("尝试JavaScript点击...")
                try:
                    # Vue登录页面使用login-btn类
                    self.page.run_js('document.querySelector(".login-btn").click()')
                    print_info("JS点击 .login-btn 成功")
                    submit_clicked = True
                except:
                    try:
                        self.page.run_js('document.querySelector("button[type=submit]").click()')
                        submit_clicked = True
                    except:
                        try:
                            self.page.run_js('document.querySelector("button").click()')
                            submit_clicked = True
                        except Exception as e:
                            print_info(f"JS点击失败: {e}")
            
            # 方法4: 按回车
            if not submit_clicked:
                print_info("尝试按回车提交...")
                password_input.input('\n')
            
            time.sleep(5)
            
            # 检查是否有验证码
            print_info("检查是否有验证码...")
            try:
                captcha = self.page.ele('tag:input@name=captcha', timeout=2)
                if captcha:
                    print_error("检测到验证码，需要手动输入")
                    self.save_debug_html("captcha")
                    return False
            except:
                pass
            
            try:
                captcha_img = self.page.ele('tag:img@src*=captcha', timeout=2)
                if captcha_img:
                    print_error("检测到验证码图片，需要手动输入")
                    return False
            except:
                pass
            
            # 处理可能的弹窗
            self.handle_popup()
            
            # 检查登录结果
            print_info(f"等待后页面: {self.page.title}")
            print_info(f"当前URL: {self.page.url}")
            
            # 再等待一会儿，有些页面跳转慢
            time.sleep(3)
            
            # 判断是否登录成功 - 成功后会跳转回电子资源平台
            if 'login' in self.page.url.lower() or '统一认证' in self.page.title:
                # 检查是否有错误提示
                error_text = None
                try:
                    error_ele = self.page.ele('.error', timeout=2)
                    if error_ele:
                        error_text = error_ele.text
                except:
                    pass
                
                if not error_text:
                    try:
                        error_ele = self.page.ele('.error-msg', timeout=2)
                        if error_ele:
                            error_text = error_ele.text
                    except:
                        pass
                
                if error_text:
                    print_error(f"登录失败: {error_text}")
                    self.save_debug_html("login_failed")
                    return False
                else:
                    # 还在登录页面但没有错误，可能是正在登录中
                    print_info("还在登录页面，等待跳转...")
                    time.sleep(5)
                    
                    # 再次检查
                    if 'login' in self.page.url.lower() or '统一认证' in self.page.title:
                        print_error("登录超时，仍在登录页面")
                        self.save_debug_html("login_timeout")
                        return False
            
            # 登录成功后会跳转到电子资源平台或其他页面
            print_success(f"登录成功！当前页面: {self.page.title}")
            print_info(f"当前URL: {self.page.url}")
            return True
            
        except Exception as e:
            print_error(f"登录出错: {e}")
            return False
    
    def goto_pkulaw(self):
        """跳转到北大法宝"""
        print_step(2, "跳转北大法宝")
        
        try:
            # 确保在电子资源平台页面
            if 'pkulaw' in self.page.url.lower():
                print_info("已经在北大法宝页面")
                self.pkulaw_page = self.page
                return True
            
            # 等待资源列表加载
            print_info("等待资源列表加载...")
            time.sleep(3)
            
            # 如果页面需要刷新才能看到资源列表
            if 'browse' in self.page.url:
                print_info("刷新页面以获取资源列表...")
                self.page.refresh()
                time.sleep(3)
            
            print_info("查找北大法宝访问入口...")
            
            # 查找北大法宝链接（可能是 "北大法宝[647ms]" 格式）
            pkulaw_link = None
            
            # 方法1: 通过包含"北大法宝"文本查找（匹配 "北大法宝[xxms]"）
            try:
                pkulaw_link = self.page.ele('text:北大法宝', timeout=3)
                if pkulaw_link:
                    link_text = pkulaw_link.text or ''
                    print_info(f"找到北大法宝入口: {link_text}")
            except:
                pass
            
            # 方法2: 遍历所有链接，找包含"北大法宝"或"法宝"的
            if not pkulaw_link:
                print_info("遍历所有链接查找...")
                links = self.page.eles('tag:a')
                print_info(f"页面共有 {len(links)} 个链接")
                for i, link in enumerate(links):
                    try:
                        text = link.text or ''
                        href = link.attr('href') or ''
                        # 打印前10个链接供调试
                        if i < 10 and text.strip():
                            print(f"  [{i}] {text[:40]} -> {href[:50]}")
                        # 匹配 "北大法宝" 或 "北大法宝[xxms]"
                        if '北大法宝' in text:
                            pkulaw_link = link
                            print_info(f"找到北大法宝链接: {text[:40]}")
                            break
                        # 如果只包含"法宝"两个字
                        if '法宝' in text and len(text.strip()) < 15 and 'href' in str(link):
                            pkulaw_link = link
                            print_info(f"找到法宝链接: {text[:40]}")
                            break
                    except Exception as e:
                        continue
            
            # 方法3: 通过class或id查找
            if not pkulaw_link:
                try:
                    pkulaw_link = self.page.ele('.pkulaw', timeout=2)
                except:
                    pass
            
            if pkulaw_link:
                # 获取链接文本和URL
                link_text = pkulaw_link.text or pkulaw_link.attr('title') or '北大法宝'
                link_href = pkulaw_link.attr('href') or ''
                print_info(f"准备点击访问入口: {link_text}")
                print_info(f"链接地址: {link_href}")
                
                # 记录当前标签页数量
                tabs_before = len(self.browser.get_tabs())
                print_info(f"点击前标签页数量: {tabs_before}")
                
                # 点击访问入口
                click_success = False
                try:
                    pkulaw_link.click()
                    click_success = True
                    print_info("已点击链接")
                except Exception as e:
                    print_info(f"直接点击失败: {e}")
                    try:
                        pkulaw_link.run_js('this.click()')
                        click_success = True
                        print_info("已使用JS点击")
                    except Exception as e2:
                        print_error(f"JS点击也失败: {e2}")
                
                if not click_success and link_href:
                    print_info(f"点击失败，直接访问链接: {link_href}")
                    if link_href.startswith('http'):
                        self.page.get(link_href)
                    else:
                        self.page.get(f"https://eds.tju.edu.cn{link_href}")
                    click_success = True
                
                if not click_success:
                    print_error("无法点击访问入口")
                    return False
                
                print_info("等待跳转...")
                time.sleep(10)  # 资源库跳转需要更长时间
                
                # 检查是否有新标签页弹出
                tabs_after = len(self.browser.get_tabs())
                print_info(f"点击后标签页数量: {tabs_after}")
                
                if tabs_after > tabs_before:
                    print_info(f"检测到新标签页弹出")
            else:
                print_info("未找到访问入口，尝试直接访问...")
                self.page.get('https://www.pkulaw.com/')
                time.sleep(3)
            
            # 检查是否弹出新标签页
            print_info("检查新标签页...")
            time.sleep(3)
            
            # 获取所有标签页
            tabs = self.browser.get_tabs()
            print_info(f"当前共有 {len(tabs)} 个标签页")
            
            # 找北大法宝标签页
            for tab in tabs:
                try:
                    if 'pkulaw' in tab.url.lower():
                        self.pkulaw_page = tab
                        print_info(f"已找到北大法宝标签页: {tab.title}")
                        break
                except:
                    continue
            
            # 如果没找到特定标签页，使用最新标签页
            if not self.pkulaw_page:
                self.pkulaw_page = self.browser.latest_tab
                print_info(f"使用最新标签页: {self.pkulaw_page.title}")
            
            # 检查是否成功进入北大法宝
            page_url = self.pkulaw_page.url.lower()
            page_title = self.pkulaw_page.title
            print_info(f"当前页面: {page_title} - {page_url}")
            
            # 成功标志：包含 pkulaw / chinalawinfo / 图书馆代理域名特征
            if 'pkulaw' in page_url or 'chinalawinfo' in page_url or '.eds.tju.edu.cn' in page_url:
                print_success(f"已进入北大法宝: {page_title}")
                return True
            
            # 如果是 entry.do 链接（图书馆资源跳转网关），等待跳转
            if 'entry.do' in page_url:
                print_info("检测到资源跳转网关，等待跳转完成...")
                time.sleep(8)
                
                # 刷新当前页面URL
                page_url = self.pkulaw_page.url.lower()
                page_title = self.pkulaw_page.title
                print_info(f"跳转后页面: {page_title} - {page_url}")
                
                # 再次检测
                if 'pkulaw' in page_url or 'chinalawinfo' in page_url or '.eds.tju.edu.cn' in page_url:
                    print_success(f"已进入北大法宝: {page_title}")
                    return True
            
            # 如果进入了资源详情页（eresourceInfo），需要再点击访问入口
            if 'eresourceinfo' in page_url or 'rid=' in page_url:
                print_info("进入资源详情页，查找访问入口...")
                time.sleep(3)
                
                # 先打印页面所有链接供调试
                print_info("页面所有链接:")
                try:
                    all_links = self.pkulaw_page.eles('tag:a')
                    for i, link in enumerate(all_links[:15]):
                        text = link.text or ''
                        href = link.attr('href') or ''
                        if text.strip():
                            print(f"  [{i}] {text[:40]} -> {href[:50]}")
                except:
                    pass
                
                # 查找访问入口按钮/链接
                access_link = None
                
                # 方法1: 找包含"北大法宝"且带延迟时间的链接（如"北大法宝[647ms]"）
                try:
                    for link in all_links:
                        text = link.text or ''
                        if '北大法宝' in text and ('ms' in text or '[' in text):
                            access_link = link
                            print_info(f"找到北大法宝访问链接: {text}")
                            break
                except:
                    pass
                
                # 方法2: 找"访问入口"文本的父元素或相邻元素
                if not access_link:
                    try:
                        access_link = self.pkulaw_page.ele('text:访问入口', timeout=3)
                        if access_link:
                            print_info("找到访问入口文本，查找关联链接...")
                            # 可能是父元素或相邻元素，直接点这个元素试试
                            # 或者查找同级的a标签
                            try:
                                parent = access_link.parent()
                                if parent:
                                    links_in_parent = parent.eles('tag:a')
                                    if links_in_parent:
                                        access_link = links_in_parent[0]
                                        print_info(f"使用父元素中的链接: {access_link.text[:40]}")
                            except:
                                pass
                    except:
                        pass
                
                # 方法3: 找包含"访问"或"进入"的按钮或链接
                if not access_link:
                    try:
                        for link in all_links:
                            text = link.text or ''
                            if '访问' in text or '进入' in text or '点击' in text:
                                access_link = link
                                print_info(f"找到访问链接: {text[:40]}")
                                break
                    except:
                        pass
                
                # 方法4: 找所有按钮
                if not access_link:
                    try:
                        buttons = self.pkulaw_page.eles('tag:button')
                        for btn in buttons:
                            btn_text = btn.text or ''
                            if '访问' in btn_text or '进入' in btn_text or '北大法宝' in btn_text:
                                access_link = btn
                                print_info(f"找到访问按钮: {btn_text}")
                                break
                    except:
                        pass
                
                # 方法5: 找包含pkulaw的链接
                if not access_link:
                    try:
                        for link in all_links:
                            href = link.attr('href') or ''
                            text = link.text or ''
                            if 'pkulaw' in href.lower() or 'chinalawinfo' in href.lower():
                                access_link = link
                                print_info(f"找到pkulaw链接: {text[:40]}")
                                break
                    except:
                        pass
                
                if access_link:
                    link_text = access_link.text or ''
                    link_href = access_link.attr('href') or ''
                    print_info(f"点击: {link_text[:50]}")
                    print_info(f"链接: {link_href}")
                    
                    # 如果是entry.do链接，直接访问更可靠
                    if 'entry.do' in link_href:
                        print_info("检测到entry.do跳转链接，直接访问...")
                        if link_href.startswith('http'):
                            self.pkulaw_page.get(link_href)
                        else:
                            self.pkulaw_page.get(f"https://eds.tju.edu.cn{link_href}")
                        
                        print_info("等待跳转完成...")
                        time.sleep(8)
                        
                        # 检查是否成功进入北大法宝
                        current_url = self.pkulaw_page.url.lower()
                        print_info(f"当前URL: {current_url}")
                        
                        # 成功标志：pkulaw / chinalawinfo / 图书馆代理域名
                        if 'pkulaw' in current_url or 'chinalawinfo' in current_url or '.eds.tju.edu.cn' in current_url:
                            print_success(f"已进入北大法宝: {self.pkulaw_page.title}")
                            return True
                        
                        # 如果还在entry.do，等待一下再检查
                        if 'entry.do' in current_url:
                            print_info("仍在跳转中，继续等待...")
                            time.sleep(5)
                            current_url = self.pkulaw_page.url.lower()
                            if 'pkulaw' in current_url or 'chinalawinfo' in current_url or '.eds.tju.edu.cn' in current_url:
                                print_success(f"已进入北大法宝: {self.pkulaw_page.title}")
                                return True
                    else:
                        # 普通点击方式
                        try:
                            access_link.click()
                        except:
                            try:
                                access_link.run_js('this.click()')
                            except Exception as e:
                                print_error(f"点击失败: {e}")
                                return False
                        
                        print_info("等待跳转...")
                        time.sleep(10)
                        
                        # 检查是否有新标签页
                        tabs_after = len(self.browser.get_tabs())
                        if tabs_after > len(all_links):
                            print_info(f"检测到新标签页")
                            for tab in self.browser.get_tabs():
                                if 'pkulaw' in tab.url.lower() or 'chinalawinfo' in tab.url.lower():
                                    self.pkulaw_page = tab
                                    print_success(f"已进入北大法宝: {tab.title}")
                                    return True
                        
                        # 检查当前页
                        if 'pkulaw' in self.pkulaw_page.url.lower() or 'chinalawinfo' in self.pkulaw_page.url.lower():
                            print_success(f"已进入北大法宝: {self.pkulaw_page.title}")
                            return True
                
                print_error("在资源详情页未找到访问入口或跳转失败")
                return False
            
            # 其他情况，尝试直接访问
            print_info(f"未进入北大法宝，尝试直接访问...")
            self.pkulaw_page.get('https://www.pkulaw.com/')
            time.sleep(5)
            
            if 'pkulaw' in self.pkulaw_page.url.lower():
                print_success(f"已进入北大法宝: {self.pkulaw_page.title}")
                return True
            else:
                print_error(f"仍无法进入北大法宝: {self.pkulaw_page.url}")
                return False
            
        except Exception as e:
            print_error(f"跳转出错: {e}")
            return False
    
    def select_database(self, db_type='法律法规'):
        """选择数据库类型：法律法规 或 司法案例"""
        print_info(f"选择数据库: {db_type}")
        
        try:
            page = self.pkulaw_page
            current_url = page.url
            print_info(f"当前URL: {current_url}")
            
            # 从当前URL中提取基础代理地址
            # 例如：https://cffgh3f953b9fbf834730swbfxonkxoxbk6w0kfxig.eds.tju.edu.cn/law?way=topGuid
            import re
            match = re.match(r'(https?://[^/]+)', current_url)
            if not match:
                print_error("无法解析当前URL")
                return False
            
            base_url = match.group(1)  # https://xxx.eds.tju.edu.cn
            
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
                print_info(f"当前URL: {page.url}")
                return True
            else:
                print_warning(f"未知的数据库类型: {db_type}，使用当前页面")
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
                print_info("无搜索关键词，使用当前页面")
                return True
            
            print_info(f"搜索关键词: {keyword}")
            
            # 打印页面所有input供调试
            print_info("查找搜索框...")
            try:
                inputs = page.eles('tag:input')
                print_info(f"页面共有 {len(inputs)} 个input")
                for i, inp in enumerate(inputs[:10]):
                    inp_id = inp.attr('id') or '无id'
                    inp_name = inp.attr('name') or '无name'
                    inp_placeholder = inp.attr('placeholder') or '无placeholder'
                    inp_type = inp.attr('type') or 'text'
                    print(f"  [{i}] id={inp_id}, name={inp_name}, placeholder={inp_placeholder}, type={inp_type}")
            except Exception as e:
                print_info(f"获取input列表失败: {e}")
            
            # 查找搜索框
            search_input = None
            selectors = [
                'tag:input@id=keyword',
                'tag:input@name=keyword', 
                'tag:input@name=kw',
                'tag:input@placeholder*=搜索',
                'tag:input@placeholder*=标题',
                'tag:input@placeholder*=关键词',
                'css:.search-input input',
                'css:.search-box input',
                'css:input[type=text]',
            ]
            
            for selector in selectors:
                try:
                    search_input = page.ele(selector, timeout=1)
                    if search_input:
                        print_info(f"找到搜索框: {selector}")
                        break
                except:
                    continue
            
            # 如果还是没找到，尝试第一个可见的text输入框
            if not search_input:
                print_info("尝试查找第一个文本输入框...")
                try:
                    inputs = page.eles('tag:input')
                    for inp in inputs:
                        inp_type = inp.attr('type') or 'text'
                        if inp_type == 'text':
                            search_input = inp
                            print_info("使用第一个文本输入框作为搜索框")
                            break
                except:
                    pass
            
            if search_input:
                # 清除并输入关键词
                search_input.clear()
                time.sleep(0.5)
                search_input.input(keyword)
                print_info(f"已输入关键词: {keyword}")
                time.sleep(1)
                
                # 执行搜索 - 使用回车
                print_info("执行搜索...")
                search_input.input('\n')
                print_info("已按回车搜索")
                
                time.sleep(5)
                print_info(f"搜索后页面: {page.title}")
                
                time.sleep(5)
                print_info(f"搜索完成: {page.title}")
                print_info(f"当前URL: {page.url}")
            else:
                print_warning("未找到搜索框，使用当前页面")
            
            return True
            
        except Exception as e:
            print_error(f"搜索出错: {e}")
            return False
    
    def collect_urls(self, max_pages=5):
        """收集URL"""
        print_step(4, f"收集URL（最多{max_pages}页）")
        
        try:
            page = self.pkulaw_page
            existing = self.read_urls()
            total_new = 0
            
            # 等待列表加载
            print_info("等待搜索结果列表加载...")
            time.sleep(3)
            
            # 点击"不分组"后，处理所有结果并分页爬取
            print_info("收集第一页数据，展开各分组...")
            
            # 第一步：点击"不分组"选项，取消分组显示
            print_info("点击'不分组'选项...")
            try:
                no_group_btn = page.ele('text:不分组', timeout=3)
                no_group_btn.click()
                print_info("已点击'不分组'，等待页面刷新...")
                time.sleep(3)
            except:
                try:
                    page.run_js('document.evaluate("//text()[contains(.,\'不分组\')]", document).iterateNext().click()')
                    print_info("已点击'不分组'，等待页面刷新...")
                    time.sleep(3)
                except Exception as e:
                    print_info(f"点击'不分组'失败: {e}")
            
            print_info("开始收集链接...")
            
            # 获取列表 - 尝试多种选择器
            target = None
            list_selectors = [
                '.result-list',      # 结果列表
                '.list-content',     # 列表内容
                'tag:tbody',         # 表格体
                '.search-result',    # 搜索结果
                '.data-list',        # 数据列表
                '#resultList',       # 结果列表ID
                '.item-list',        # 项目列表
            ]
            
            for selector in list_selectors:
                try:
                    target = page.ele(selector, timeout=1)
                    if target:
                        print_info(f"找到列表: {selector}")
                        break
                except:
                    continue
            
            items = []
            
            if not target:
                # 尝试找任何包含链接的列表区域
                print_info("尝试查找列表区域...")
                try:
                    # 找包含多个链接的区域
                    all_links = page.eles('tag:a')
                    print_info(f"页面共有 {len(all_links)} 个链接")
                    
                    # 打印前几个链接供调试
                    for i, link in enumerate(all_links[:10]):
                        href = link.attr('href') or ''
                        text = link.text or ''
                        if text.strip() and len(text) > 5:
                            print(f"  样例链接[{i}]: {text[:40]} -> {href[:60]}")
                            if i >= 5:
                                break
                    
                    # 如果没有找到列表容器，直接遍历所有链接
                    if len(all_links) > 5:
                        for link in all_links:
                            href = link.attr('href') or ''
                            text = link.text or ''
                            # 过滤出法律法规或案例链接（同时检查href和文本）
                            if ('law' in href or 'case' in href or 'detail' in href or 
                                'chl' in href or 'article' in href or
                                '法规' in text or '法律' in text or '规划' in text):
                                if len(text) > 5:  # 有实际标题
                                    items.append(link)
                        if items:
                            print_info(f"找到 {len(items)} 个可能的结果链接")
                except Exception as e:
                    print_info(f"查找链接出错: {e}")
                
                if not items:
                    print_info("未找到列表，可能无搜索结果")
                    return 0
            else:
                # 获取列表项
                try:
                    items = target.eles('tag:tr') or target.eles('.list-item') or target.eles('.item') or target.eles('tag:li')
                    print_info(f"从列表中找到 {len(items)} 个条目")
                except Exception as e:
                    print_info(f"获取列表项出错: {e}")
            
            if not items:
                print_info("本页无数据")
                return 0
            
            print_info(f"找到 {len(items)} 个条目")
            
            print_info(f"开始处理 {len(items)} 个条目...")
            page_new = 0
            for i, item in enumerate(items):
                try:
                    # 显示进度
                    if i % 10 == 0:
                        print(f"\r  处理中... {i}/{len(items)}", end='', flush=True)
                    
                    # 如果是元素对象，查找链接
                    if hasattr(item, 'ele'):
                        try:
                            link = item.ele('tag:a', timeout=1)
                        except:
                            continue
                    else:
                        # 已经是链接元素
                        link = item
                    
                    if link:
                        url = link.attr('href')
                        title = link.text or ''
                        
                        if url and title:
                            # 补全URL
                            if url.startswith('/'):
                                url = 'https://www.pkulaw.com' + url
                            elif not url.startswith('http'):
                                url = 'https://www.pkulaw.com/' + url
                            
                            # 过滤非详情页链接（放宽条件）
                            # 北大法宝详情页链接通常包含 law/case/detail/article/chl 或者是具体的文档ID
                            url_lower = url.lower()
                            is_valid = ('/law' in url_lower or '/case' in url or 'detail' in url_lower or 
                                       '/article' in url_lower or '/chl' in url_lower or 
                                       '/pfnl' in url_lower or  # 司法案例
                                       'docid' in url_lower or  # 文档ID
                                       len(url) > 50)  # 较长的URL通常是详情页
                            
                            if is_valid:
                                if url not in existing:
                                    existing.add(url)
                                    self.append_url(url)
                                    page_new += 1
                                    total_new += 1
                                    if page_new <= 5:  # 打印前5个收集的URL
                                        print(f"  [收集] {title[:30]}... -> {url[:60]}")
                                    
                                    # 每收集10个打印一次
                                    if page_new % 10 == 0:
                                        print(f"\r  已收集 {page_new} 个URL", end='', flush=True)
                except Exception as e:
                    continue
            
            print()  # 换行
            print_success(f"第1页新增 {page_new} 个URL")
            
            # 翻页收集
            for page_num in range(2, max_pages + 1):
                print_info(f"处理第 {page_num} 页...")
                
                try:
                    # 查找下一页按钮
                    next_btn = None
                    for selector in ['text:下一页', '.next', '.pagination-next', '[title*=下一页]', '[class*=next]']:
                        try:
                            next_btn = page.ele(selector, timeout=2)
                            if next_btn:
                                # 检查是否禁用
                                btn_class = next_btn.attr('class') or ''
                                if 'disabled' not in btn_class and '禁' not in btn_class:
                                    print_info(f"找到下一页按钮: {selector}")
                                    break
                                else:
                                    next_btn = None  # 禁用状态，继续找
                        except:
                            continue
                    
                    if next_btn:
                        print_info("点击下一页...")
                        try:
                            next_btn.click()
                        except:
                            print_info("直接点击失败，使用JS点击...")
                            next_btn.run_js('this.click()')
                        time.sleep(3)
                        
                        # 收集当前页
                        items = []
                        try:
                            all_links = page.eles('tag:a')
                            print_info(f"第{page_num}页共有 {len(all_links)} 个链接")
                            
                            # 打印前几个链接供调试
                            for i, link in enumerate(all_links[:5]):
                                href = link.attr('href') or ''
                                text = link.text or ''
                                print(f"  样例链接[{i}]: {text[:30]} -> {href[:60]}")
                            
                            for link in all_links:
                                href = link.attr('href') or ''
                                if 'law' in href or 'case' in href or 'detail' in href or 'article' in href or 'chl' in href:
                                    items.append(link)
                            print_info(f"过滤后找到 {len(items)} 个可能的结果链接")
                        except Exception as e:
                            print_info(f"收集链接出错: {e}")
                        
                        page_new = 0
                        for item in items:
                            try:
                                if hasattr(item, 'attr'):
                                    url = item.attr('href')
                                    title = item.text or ''
                                    
                                    if url and title:
                                        if url.startswith('/'):
                                            url = 'https://www.pkulaw.com' + url
                                        elif not url.startswith('http'):
                                            url = 'https://www.pkulaw.com/' + url
                                        
                                        # 放宽过滤条件
                                        url_lower = url.lower()
                                        is_valid = ('/law' in url_lower or '/case' in url or 'detail' in url_lower or 
                                                   '/article' in url_lower or '/chl' in url_lower or 
                                                   '/pfnl' in url_lower or 'docid' in url_lower or len(url) > 50)
                                        
                                        if is_valid:
                                            if url not in existing:
                                                existing.add(url)
                                                self.append_url(url)
                                                page_new += 1
                                                total_new += 1
                            except:
                                continue
                        
                        print_success(f"第{page_num}页新增 {page_new} 个URL")
                    else:
                        print_info("无下一页按钮，结束收集")
                        break
                        
                except Exception as e:
                    print_info(f"翻页出错: {e}")
                    break
            
            print_success(f"共收集 {total_new} 个URL")
            print_info(f"URL已保存到: {self.urls_file}")
            return total_new
            
        except Exception as e:
            print_error(f"收集出错: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def download_cases(self):
        """下载案件"""
        print_step(5, "下载案件")
        
        try:
            urls = self.read_urls()
            if not urls:
                print_info("无URL需要下载")
                return 0
            
            total = len(urls)
            print_info(f"共 {total} 个案件待下载")
            
            page = self.pkulaw_page
            success = 0
            
            for i, url in enumerate(list(urls)[:10000]):
                try:
                    self.wait(2, 4)
                    
                    page.get(url)
                    time.sleep(2)
                    
                    # 获取内容
                    title = ""
                    content = ""
                    try:
                        wrap = page.ele('.fulltext-wrap')
                        title = wrap.ele('.title').text
                        content = wrap.ele('.content').text
                    except:
                        try:
                            title = page.ele('.title').text
                            content = page.ele('.fulltext').text
                        except:
                            title = page.title
                            content = page.html
                    
                    # 保存
                    for c in "*?:<>|/\\":
                        title = title.replace(c, '某')
                    
                    filepath = os.path.join(self.folder_path, f'{title}.txt')
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.remove_url(url)
                    success += 1
                    
                    print_progress(i + 1, total, title[:25])
                    
                except Exception as e:
                    continue
            
            print_success(f"下载完成: 成功 {success}/{total}")
            return success
            
        except Exception as e:
            print_error(f"下载出错: {e}")
            return 0
    
    def read_urls(self):
        """读取URL"""
        urls = set()
        if os.path.exists(self.urls_file):
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        urls.add(url)
        return urls
    
    def append_url(self, url):
        """添加URL"""
        with open(self.urls_file, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
    
    def remove_url(self, url):
        """删除URL"""
        urls = self.read_urls()
        urls.discard(url)
        with open(self.urls_file, 'w', encoding='utf-8') as f:
            for u in urls:
                f.write(u + '\n')
    
    def save_debug_html(self, name):
        """保存调试HTML"""
        try:
            html = self.page.html
            path = os.path.join(self.folder_path, f'debug_{name}_{int(time.time())}.html')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            print_info(f"调试文件: {path}")
        except:
            pass
    
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
        
        # 4. 选择数据库并搜索
        self.search_cases(keyword, db_type)
        time.sleep(2)
        
        # 5. 收集URL
        collected = self.collect_urls(max_pages)
        
        # 6. 下载
        downloaded = 0
        if collected > 0:
            downloaded = self.download_cases()
        
        # 统计
        elapsed = time.time() - start
        print_header("运行统计")
        print_info(f"运行时间: {elapsed:.1f} 秒")
        print_info(f"数据库类型: {db_type}")
        print_info(f"搜索关键词: {keyword if keyword else '无'}")
        print_info(f"收集URL: {collected} 个")
        print_info(f"下载成功: {downloaded} 个")
        print_info(f"下载目录: {self.folder_path}")
        
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
    max_pages = input("最大翻页数（默认5）: ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 5
    
    print()
    print("=" * 50)
    print(f"数据库类型: {db_type}")
    print(f"搜索关键词: {keyword if keyword else '无'}")
    print(f"最大翻页数: {max_pages}")
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
