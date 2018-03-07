# -*- coding: utf-8 -*-
import time
import wda
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from PIL import Image

# 截图距离 * time_coefficient = 按键时长
# time_coefficient:
#    iphonex: 0.00125
#    iphone6: 0.00196
#    iphone6s plus: 0.00120
time_coefficient = 0.00120


c = wda.Client()
s = c.session()


def pull_screenshot():
    c.screenshot('autojump.png')


def jump(distance):
    press_time = distance * time_coefficient
    press_time = press_time
    print('press_time = ',press_time)
    s.tap_hold(200, 200, press_time)


fig = plt.figure() #生成一个新的图形
pull_screenshot() #wda截屏
img = np.array(Image.open('autojump.png'))  #以阵列方式打开图形
im = plt.imshow(img, animated=True) #展示图形,animated为自定义参数

#只初始设置一次，此后将由on_click循环
update = True
click_count = 0
cor = []


def update_data():
    return np.array(Image.open('autojump.png'))


def updatefig(*args):
    global update
    if update:
        time.sleep(1)
        pull_screenshot()
        im.set_array(update_data())
        update = False
    return im,


def on_click(event):
    global update
    global ix, iy
    global click_count
    global cor

    ix, iy = event.xdata, event.ydata #获取点的x，y坐标值

    #为中间重新开玩，刷新二次页面，若其中有一次为范围为100，100内，则重玩
    retry_play = False
    if ix <= 100 and iy <= 100:retry_play = True

    coords = [(ix, iy)]
    print('now = ', coords)
    cor.append(coords) #将点击坐标纳入列表

    click_count += 1 #一次点击增加一个坐标，增加一个点击统计
    if click_count > 1: #如果有两个图标，那么就是第一个是棋子，第二个棋台
        click_count = 0 #清空
        cor1 = cor.pop() #棋子或棋台坐标1
        cor2 = cor.pop() #棋子或棋台坐标2

        distance = (cor1[0][0] - cor2[0][0])**2 + (cor1[0][1] - cor2[0][1])**2 #三角函数，三角求边
        distance = distance ** 0.5
        if retry_play == True:
            distance = 1
        print('distance = ', distance)
        jump(distance)#跳
        update = True


fig.canvas.mpl_connect('button_press_event', on_click)  #为pyplot下的响应画布点击功能，除非关闭，否则一直响应点击状态
# 因此循环在on_click里了
ani = animation.FuncAnimation(fig, updatefig, interval=50, blit=True) #刷新图像
plt.show()
