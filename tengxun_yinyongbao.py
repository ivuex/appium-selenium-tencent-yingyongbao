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

    def toggle_to_ranklist(self): # 切换到app爬行榜列表页
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

    def fetch_ranklist(self): # 获取itemEles并循环
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
