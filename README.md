## 前言
###### python爬取移动端app数据的常用方式有
 + 模拟正常请求，获得json，加密后的数据等，并清洗及存储
    - 可能需要解决的问题有
        * token及其他参数的获取与计算
    - 常用(包括但不限于)的请求库
        * urlib
        * requests
 + 移动端app接入http代理，在代理中获得数据并清洗及储存
    - 常用(包括但不限于)的代理软件及特点
        * Fiddler: Gui视窗，号称Windows下最好的抓包工具，可替换请求文件等
        * Charles: Gui视窗，支持Linux，Mac，Windows，可以Map Remote, Map Local, Breakpoints，自动保存指定请求等。 详见[http://spiders.zhouyu.wiki/posts/gao-ke-pei-zhi-de-charle-szhua-bao-gong-ju/](http://spiders.zhouyu.wiki/posts/gao-ke-pei-zhi-de-charle-szhua-bao-gong-ju/)，用这个基本可以不用postman
        * Mitmproxy: Terminal+Webui，提供Api，可与各爬虫开发语言无缝对接，详见 [https://docs.mitmproxy.org/stable/](https://docs.mitmproxy.org/stable/)
        * AnyProxy: 只提供api，可以使用Node.js定制和扩展，详见 [https://github.com/alibaba/anyproxy/blob/master/docs/cn/src_doc.md](https://github.com/alibaba/anyproxy/blob/master/docs/cn/src_doc.md)
 + Appium按参数接入移动端App，使用各爬虫开发语言调用Appium提供的Api模拟真人操作移动端App，获得数据并清洗及储存
###### 爬虫开发过程中可根据数据目标实情，合理选择以上三种方案
 + 这里使用Appium实现对 **腾讯应用宝**所列出的App**排行榜**数据 页面进行限定条数的爬取
## 实现
###### 安装
 + 按照[appium，java，adroid-sdk的安装](http://localhost/posts/mac-an-zhuang-appium/)完成appium环境安装及配置
 + 执行以下命令完成所需的python库
```
pip3 install Appium-Python-Client selenium
```
###### 遇到的问题
 + 腾讯的应用宝的可滑动元素不支持 appium 的swipe方法，因为有tab栏
    - 解决方案
        * 根据xpath获取到 itemEle (就是一条目标数据的 WebElement) 的列表 itemEles
        * 在当前获取到的 WebElement 被解析处理后执行 滚动的方法链 的代码:
```
TouchAction(self.driver).press(itemEles[-1]).move_to(itemEles[0]).release().perform()
```

 + 爬取过程中，偶有 itemEle 获取不到加载了目标数据属性值的 子WebElement，实际上是两种情况：
    - 头顶上的banner元素不是目标元素，但仍然被选中了，而且这是有时有，有时没有的(以前爬数据较多时经常遇到这种情况)，解决方案如下
        * 在提取数据的方法*parseItemEle*中获取该相关字节点时捕获selenium.common.exceptions.NoSuchElementException异常
        * return None
        * 在该解析数据方法的调用方法fetch_ranklist的itemEles迭代代码开头执行 continue 跳过处理该元素
    - 当当前迭代的itemEle是当前itemEles中的最后一项时，由于该元素没有（未曾）完全显示在手机屏幕中，所以相关元素没有被加载，解决方案如下
        * 在提取数据的方法*parseItemEle*中获取该相关字节点时捕获selenium.common.exceptions.NoSuchElementException异常，可以输出日志或pass
        * 在下一次执行TouchAction滚动的方法链后，该元素会加载完成并可顺利爬取爬取

###### 代码
```
# -*- coding:utf-8 -*-

import time
from appium import webdriver
from selenium.common.exceptions import NoSuchAttributeException, NoSuchElementException
from appium.webdriver.common.touch_action import TouchAction

from mongo import collection

import settings

class Crawler():
    def __init__(self):
        self.crawl_done = False
        self.limit = 90
        self.ranklist_ids = []
        desired_caps = {
            "platformName": settings.platformName,
            "deviceName": settings.deviceName,
            "platformVersion": settings.platformVersion,
            "appPackage": "com.tencent.android.qqdownloader",
            "appActivity": "com.tencent.assistantv2.activity.MainActivity",
            'noReset': True,
        }
        print(desired_caps)
        self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
        # self.swipe_ele = self.driver.find_element_by_id('com.tencent.android.qqdownloader:id/oh') # 这是可滑动的app列表元素

    def toggle_to_ranklist(self):  # 切换到app爬行榜列表页
        time.sleep(3)
        ranklist = self.driver.find_element_by_xpath('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.support.v4.view.ViewPager/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.ListView/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.RelativeLayout[2]/android.widget.LinearLayout/android.widget.TextView')
        print(ranklist)
        ranklist.click()
        print('Toggled into ranklist sub tab.')
        time.sleep(3)
        self.fetch_ranklist()

    def parseItemEle(self, itemEle):
        try:
            id = int(itemEle.find_element_by_id('com.tencent.android.qqdownloader:id/ox').text)
            if id in self.ranklist_ids:
                print('This app item has been processed.')
                return None
            if id > self.limit:
                print('Crawl finished.')
                raise(StopIteration)
        except NoSuchElementException:
            print('Cannot got app item id, it is not the expected app item WebElement. skip.')
            return None
        try:
            appName = itemEle.find_element_by_id('com.tencent.android.qqdownloader:id/ki').text
            tagEles = itemEle.find_elements_by_id('com.tencent.android.qqdownloader:id/bat')
            tag = tagEles[0].text if len(tagEles) else ''
            a_word = itemEle.find_element_by_id('com.tencent.android.qqdownloader:id/kd').text
            category = itemEle.find_element_by_id('com.tencent.android.qqdownloader:id/baw').text
            size = itemEle.find_element_by_id('com.tencent.android.qqdownloader:id/bax').text
            app = {
                'id': id,
                'appName': appName,
                'tag': tag,
                'a_word': a_word,
                'category': category,
                'size': size,
            }
            return app
        except NoSuchElementException:
            # print('This WebElement has(did) not been seen in screen, so it will be processed in next circle.')
            raise(NoSuchElementException)

    def fetch_ranklist(self):  # 获取itemEles并循环
        itemEles = self.driver.find_elements_by_xpath('//android.widget.ListView/android.widget.RelativeLayout')
        print(itemEles)
        try:
            for itemEle in itemEles:
                app = self.parseItemEle(itemEle)
                if not app: # 如果parseItemEle方法返回值为None，那么该WebElement不是预期的 app item WebElement, 所以需要跳过
                    continue
                else:
                    collection.insert(app)
                    print(app)
                self.ranklist_ids.append(app['id'])
        except NoSuchElementException:
            if itemEle == itemEles[-1]: # 当当前itemEle是当前作用域生命周期中中itemEles中的最后一项时，由于该元素没有（未曾）完全显示在手机屏幕中，所以该itemEle会在下个循环中处理
                print('This WebElement has(did) not been seen in screen, so it will be processed in next circle.')
                pass
        except StopIteration:
            # 收到了StopIteration异常，就将self.crawl_done设置为True
            self.crawl_done = True
            return
        finally:
            step = 5
            if len(itemEles) < step:
                self.crawl_done = True
            else:
                TouchAction(self.driver).press(itemEles[-1]).move_to(itemEles[0]).release().perform()
                time.sleep(2) # 等待请求和相关WebElement加载完成
            if not self.crawl_done:  # 如果self.crawl_done为假，自调用方法self.fetch_ranklist
                self.fetch_ranklist()


if __name__ == '__main__':
    crawler = Crawler()
    crawler.toggle_to_ranklist()
```

