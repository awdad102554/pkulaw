#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北大法宝司法案例高级检索 - 交互式筛选版
流程：登录 → 跳转 → 进入高级检索 → 用户选择法院级别 & 输入案由 → 设置条件 → 保存HTML

使用方法:
    python 北大法宝司法案例高级检索.py
"""

import re
import time
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 北大法宝图书馆自动爬虫 import PkulawCrawler, print_info, print_success, print_error, print_step, print_warning


class CaseAdvancedSearchCrawler(PkulawCrawler):
    def wait(self, min_sec=1, max_sec=2):
        sec = random.uniform(min_sec, max_sec)
        print_info(f"等待 {sec:.1f} 秒...")
        time.sleep(sec)

    def goto_advanced_case(self):
        """进入司法案例高级检索页面"""
        print_step(3, "进入司法案例高级检索")
        try:
            base = self._get_base_url()
            url = base + '/advanced/case/pfnl'
            print_info(f"访问: {url}")
            self.pkulaw_page.get(url)
            time.sleep(5)
            print_info(f"当前页面: {self.pkulaw_page.title}")

            # 轮询等待页面关键异步元素加载（最多30秒）
            print_info("等待页面异步元素加载...")
            for i in range(30):
                ready = self.pkulaw_page.run_js('''
                    (function(){
                        var inputs = document.querySelectorAll('input');
                        for (var i=0; i<inputs.length; i++) {
                            var ph = inputs[i].getAttribute('placeholder') || '';
                            if (ph.indexOf('最多5个词语') !== -1) return 'ready';
                        }
                        var spans = document.querySelectorAll('span');
                        for (var i=0; i<spans.length; i++) {
                            if (spans[i].textContent.trim() === '法院级别') return 'ready';
                        }
                        return '';
                    })()
                ''', as_expr=True)
                if ready:
                    print_info(f"页面元素已就绪 (等待了 {i+1} 秒)")
                    break
                time.sleep(1)
            else:
                print_warning("页面元素加载超时，继续执行...")
            return True
        except Exception as e:
            print_error(f"进入高级检索页面失败: {e}")
            return False

    def _get_base_url(self):
        current_url = self.pkulaw_page.url
        match = re.match(r'(https?://[^/]+)', current_url)
        return match.group(1) if match else current_url.rstrip('/')

    def click_add_filter(self, filter_name, max_retry=3):
        """点击左侧 '+筛选条件' 按钮，支持多个class容器，带重试"""
        print_info(f"点击'+{filter_name}'...")
        try:
            page = self.pkulaw_page

            for attempt in range(max_retry):
                clicked = False

                # 策略1: DP ele查找并点击
                for selector in [
                    f'css:.noShow-tree-content .content span:text({filter_name})',
                    f'css:.left-tree-content .content span:text({filter_name})',
                    f'css:.left-tree-content span:text({filter_name})',
                    f'text:{filter_name}',
                ]:
                    try:
                        btn = page.ele(selector, timeout=2)
                        if btn:
                            el = btn
                            for _ in range(3):
                                if not el:
                                    break
                                cls = el.attr('class') or ''
                                if 'content' in cls:
                                    el.run_js('this.click()')
                                    clicked = True
                                    break
                                el = el.parent()
                            if not clicked:
                                btn.run_js('this.click()')
                                clicked = True
                            break
                    except:
                        continue

                # 策略2: JS遍历多个容器查找
                if not clicked:
                    clicked = page.run_js(f'''
                        var containers = [
                            '.noShow-tree-content',
                            '.left-tree-content',
                            '.el-tree-node__children',
                            '.el-tree'
                        ];
                        for (var c=0; c<containers.length; c++){{
                            var contents = document.querySelectorAll(containers[c] + ' .content');
                            if (contents.length === 0){{
                                contents = document.querySelectorAll(containers[c] + ' .el-tree-node__content');
                            }}
                            if (contents.length === 0){{
                                contents = document.querySelectorAll(containers[c] + ' .custom-tree-node');
                            }}
                            for (var i=0; i<contents.length; i++){{
                                var spans = contents[i].querySelectorAll("span, .label");
                                var hasIcon = false, hasText = false;
                                for (var j=0; j<spans.length; j++){{
                                    var cls = spans[j].className || '';
                                    var txt = spans[j].textContent.trim();
                                    if (cls.indexOf("add_icon") !== -1 || cls.indexOf("el-icon-plus") !== -1) hasIcon = true;
                                    if (txt === "{filter_name}" || txt.indexOf("{filter_name}") !== -1) hasText = true;
                                }}
                                if (hasIcon && hasText){{
                                    contents[i].click();
                                    return true;
                                }}
                            }}
                        }}
                        var allSpans = document.querySelectorAll('span');
                        for (var i=0; i<allSpans.length; i++){{
                            if (allSpans[i].textContent.trim() === "{filter_name}"){{
                                var p = allSpans[i].parentElement;
                                for (var k=0; k<5 && p; k++){{
                                    var pc = p.className || '';
                                    if (pc.indexOf('content') !== -1 || pc.indexOf('el-tree-node__content') !== -1 || pc.indexOf('custom-tree-node') !== -1){{
                                        p.click();
                                        return true;
                                    }}
                                    p = p.parentElement;
                                }}
                            }}
                        }}
                        return false;
                    ''')

                if clicked:
                    print_info(f"'+{filter_name}' 点击完成")
                    time.sleep(0.5)
                    return True

                if attempt < max_retry - 1:
                    print_warning(f"未找到'+{filter_name}'，第{attempt+1}次重试...")
                    time.sleep(2)

            print_error(f"未找到'+{filter_name}'按钮")
            return False
        except Exception as e:
            print_error(f"点击'+{filter_name}'出错: {e}")
            return False

    def set_court_level(self, mode):
        """
        设置法院级别
        mode: 'mid' -> 最高+高级+中级
              'high' -> 最高+高级
        """
        values = {
            'mid': ['01', '02', '03'],
            'high': ['01', '02']
        }
        selected = values.get(mode, values['mid'])

        for attempt in range(3):
            try:
                result = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var selected = {selected!r};
                        var cbs = document.querySelectorAll('.el-checkbox-group .el-checkbox__original');
                        if (cbs.length === 0) {{
                            cbs = document.querySelectorAll('input[type="checkbox"].el-checkbox__original');
                        }}
                        var matched = 0;
                        for (var i=0; i<cbs.length; i++){{
                            var cb = cbs[i];
                            if (selected.indexOf(cb.value) !== -1){{
                                cb.checked = true;
                                cb.dispatchEvent(new Event('change', {{bubbles: true}}));
                                var label = cb.closest ? cb.closest('label') : null;
                                if (!label) {{
                                    var p = cb.parentElement;
                                    while (p && p.tagName !== 'LABEL') p = p.parentElement;
                                    label = p;
                                }}
                                if (label){{
                                    var span = label.querySelector('.el-checkbox__input');
                                    if (span) span.classList.add('is-checked');
                                    label.classList.add('is-checked');
                                }}
                                matched++;
                            }}
                        }}
                        return matched;
                    }})()
                ''', as_expr=True)
                print_info(f"已勾选 {result} 个法院级别选项")
                if result == 0 and attempt < 2:
                    print_warning("法院级别复选框未加载，等待后重试...")
                    time.sleep(2)
                    continue
                time.sleep(0.5)
                return True
            except Exception as e:
                print_error(f"设置法院级别失败: {e}")
                return False
        return False

    def set_case_gist(self, text, max_retry=3):
        """设置案由：先选择下拉类型（民事/行政），再填入文本并回车，带重试"""
        dropdown_map = {
            '劳动争议、人事争议': '民事',
            '行政': '行政',
        }
        dropdown_type = dropdown_map.get(text, '全部')
        print_info(f"设置案由: {text} (下拉: {dropdown_type})")

        try:
            for attempt in range(max_retry):
                # ========== 步骤1：找到案由区域并展开下拉框 ==========
                r1 = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var titles = document.querySelectorAll('.fb-title');
                        var gistItem = null;
                        for (var t=0; t<titles.length; t++){{
                            if (titles[t].textContent.trim() === '案由'){{
                                var p = titles[t].parentElement;
                                while (p && !p.classList.contains('item')) p = p.parentElement;
                                gistItem = p;
                                break;
                            }}
                        }}
                        if (!gistItem){{
                            var gistDiv = document.querySelector('[property="CaseGist"]');
                            if (gistDiv) gistItem = gistDiv.querySelector('.item');
                        }}
                        if (!gistItem) return 'NOT_FOUND_ITEM';

                        var chooseTypeSelect = gistItem.querySelector('.chooseType .el-select');
                        if (!chooseTypeSelect) chooseTypeSelect = gistItem.querySelector('.el-select.fb-mini');
                        if (!chooseTypeSelect) return 'NOT_FOUND_DROPDOWN';

                        var selectInput = chooseTypeSelect.querySelector('input.el-input__inner');
                        if (!selectInput) return 'NOT_FOUND_DROPDOWN_INPUT';

                        selectInput.click();
                        selectInput.focus();
                        return 'clicked';
                    }})()
                ''', as_expr=True)
                if not r1 or (isinstance(r1, str) and r1.startswith('NOT_FOUND')):
                    if attempt < max_retry - 1:
                        print_warning(f"展开下拉框失败，第{{attempt+1}}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"展开下拉框失败: {{r1}}")
                    return False

                # 等待下拉框选项渲染
                time.sleep(0.6)

                # ========== 步骤2：点击选项 + 填入输入框 ==========
                r2 = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var dropdownType = "{dropdown_type}";
                        var text = "{text}";

                        var titles = document.querySelectorAll('.fb-title');
                        var gistItem = null;
                        for (var t=0; t<titles.length; t++){{
                            if (titles[t].textContent.trim() === '案由'){{
                                var p = titles[t].parentElement;
                                while (p && !p.classList.contains('item')) p = p.parentElement;
                                gistItem = p;
                                break;
                            }}
                        }}
                        if (!gistItem){{
                            var gistDiv = document.querySelector('[property="CaseGist"]');
                            if (gistDiv) gistItem = gistDiv.querySelector('.item');
                        }}
                        if (!gistItem) return 'NOT_FOUND_ITEM';

                        // 1) 选择下拉选项（全局精确查找 + 兜底）
                        var dropdown = document.querySelector('.el-select-dropdown.chooseType-select');
                        if (!dropdown || dropdown.style.display === 'none'){{
                            var allDropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                            for (var d=0; d<allDropdowns.length; d++){{
                                if (allDropdowns[d].style.display !== 'none'){{
                                    dropdown = allDropdowns[d];
                                    break;
                                }}
                            }}
                        }}
                        if (dropdown){{
                            var items = dropdown.querySelectorAll('.el-select-dropdown__item');
                            for (var i=0; i<items.length; i++){{
                                if (items[i].textContent.trim() === dropdownType){{
                                    items[i].click();
                                    break;
                                }}
                            }}
                        }}

                        // 2) 填入输入框
                        var searchInputs = gistItem.querySelectorAll('input');
                        var targetInput = null;
                        for (var i=0; i<searchInputs.length; i++){{
                            var ph = searchInputs[i].getAttribute('placeholder') || '';
                            if (ph.indexOf('最多5个词语') !== -1 || searchInputs[i].name === 'text'){{
                                targetInput = searchInputs[i];
                                break;
                            }}
                        }}
                        if (!targetInput) return 'NOT_FOUND_INPUT';

                        targetInput.focus();
                        targetInput.click();
                        targetInput.removeAttribute('readonly');
                        targetInput.value = text;
                        targetInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                        targetInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'wait-enter';
                    }})()
                ''', as_expr=True)
                if not r2 or (isinstance(r2, str) and r2.startswith('NOT_FOUND')):
                    if attempt < max_retry - 1:
                        print_warning(f"选择下拉或填输入框失败，第{{attempt+1}}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"选择下拉或填输入框失败: {{r2}}")
                    return False

                # ========== 步骤3：等待后回车 ==========
                if r2 == 'wait-enter':
                    print_info("等待 1 秒后回车确认...")
                    time.sleep(1)
                    self.pkulaw_page.run_js('''
                        (function(){
                            var titles = document.querySelectorAll('.fb-title');
                            var gistItem = null;
                            for (var t=0; t<titles.length; t++){
                                if (titles[t].textContent.trim() === '案由'){
                                    var p = titles[t].parentElement;
                                    while (p && !p.classList.contains('item')) p = p.parentElement;
                                    gistItem = p;
                                    break;
                                }
                            }
                            if (!gistItem){
                                var gistDiv = document.querySelector('[property="CaseGist"]');
                                if (gistDiv) gistItem = gistDiv.querySelector('.item');
                            }
                            if (!gistItem) return;

                            var searchInputs = gistItem.querySelectorAll('input');
                            var targetInput = null;
                            for (var i=0; i<searchInputs.length; i++){
                                var ph = searchInputs[i].getAttribute('placeholder') || '';
                                if (ph.indexOf('最多5个词语') !== -1 || searchInputs[i].name === 'text'){
                                    targetInput = searchInputs[i];
                                    break;
                                }
                            }
                            if (targetInput){
                                targetInput.removeAttribute('readonly');
                                targetInput.focus();
                                targetInput.click();
                                targetInput.dispatchEvent(new KeyboardEvent('keydown', {
                                    key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true
                                }));
                                targetInput.dispatchEvent(new KeyboardEvent('keypress', {
                                    key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true
                                }));
                                targetInput.dispatchEvent(new KeyboardEvent('keyup', {
                                    key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true
                                }));
                                targetInput.blur();
                            }
                        })()
                    ''', as_expr=True)
                    print_info("案由已设置 (direct-input)")
                else:
                    print_info(f"案由已设置 ({{r2}})")
                time.sleep(0.5)
                return True
        except Exception as e:
            print_error(f"设置案由失败: {{e}}")
            return False

    def click_search(self):
        """点击检索按钮"""
        print_info("点击检索按钮...")
        try:
            self.pkulaw_page.run_js('''
                (function(){
                    var btns = document.querySelectorAll('button');
                    for (var i=0; i<btns.length; i++){
                        if (btns[i].textContent.trim() === '检索'){
                            btns[i].click();
                            return true;
                        }
                    }
                    return false;
                })()
            ''', as_expr=True)
            time.sleep(3)
            return True
        except Exception as e:
            print_error(f"点击检索失败: {e}")
            return False

    def save_current_html(self, filename):
        try:
            html = self.pkulaw_page.html
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            print_success(f"页面HTML已保存: {filepath} ({len(html)} 字符)")
            return True
        except Exception as e:
            print_error(f"保存HTML失败: {e}")
            return False


def print_header(text):
    print(f"\n{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}\n")


def main():
    print_header("北大法宝司法案例高级检索")

    # 清理旧HTML
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for f in os.listdir(base_dir):
        if f.startswith('advanced_case_') and f.endswith('.html'):
            try:
                os.remove(os.path.join(base_dir, f))
                print_info(f"已删除旧文件: {f}")
            except:
                pass

    # 用户交互：选择法院级别
    print("\n请选择法院级别模式:")
    print("  1. 中级（最高人民法院 + 高级人民法院 + 中级人民法院）")
    print("  2. 高级（最高人民法院 + 高级人民法院）")
    court_choice = input("请选择 (1/2，默认1): ").strip()
    court_mode = 'high' if court_choice == '2' else 'mid'

    # 用户交互：选择案由
    print("\n请选择案由:")
    print("  1. 劳动争议、人事争议")
    print("  2. 行政")
    case_choice = input("请选择 (1/2，默认1): ").strip()
    case_gist_text = "行政" if case_choice == "2" else "劳动争议、人事争议"

    print("\n" + "="*50)
    print(f"法院级别: {'中级' if court_mode == 'mid' else '高级'}")
    print(f"案由: {case_gist_text if case_gist_text else '无'}")
    print("="*50)
    confirm = input("\n确认开始？(Y/n): ").strip().lower()
    if confirm and confirm not in ['y', 'yes', '是']:
        print("已取消")
        return

    crawler = CaseAdvancedSearchCrawler()

    try:
        if not crawler.init_browser():
            return
        if not crawler.login_library():
            print_error("登录失败")
            return
        crawler.wait()
        if not crawler.goto_pkulaw():
            print_error("跳转失败")
            return
        crawler.wait()
        if not crawler.goto_advanced_case():
            return

        # 先设置案由（此时 CaseGist 面板还显示案由输入框）
        if case_gist_text:
            if not crawler.set_case_gist(case_gist_text):
                print_warning("案由设置可能未成功，继续执行...")
            crawler.wait(0.5, 1)

        # 再点击左侧筛选条件展开面板
        filters_to_add = ['法院级别', '审理法院', '审理程序']
        for f in filters_to_add:
            crawler.click_add_filter(f)
            crawler.wait(0.5, 1)

        # 设置法院级别
        if not crawler.set_court_level(court_mode):
            return

        # 点击检索
        crawler.click_search()

        # 保存最终页面
        crawler.save_current_html('advanced_case_result.html')
        print_success("任务完成！")

    except KeyboardInterrupt:
        print("\n已中止")
    except Exception as e:
        print_error(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        print_info("浏览器保持打开，请观察页面状态。")
        print_info("观察完毕后，在此终端按 Ctrl+C 或关闭窗口即可。")
        # 阻塞主线程，保持脚本运行，浏览器不关闭
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n已结束")


if __name__ == '__main__':
    main()
